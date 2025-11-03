#!/usr/bin/env python3
"""
Voice API Backend - Connects voice interface to Intake Agent
=============================================================

This FastAPI backend receives voice transcripts and returns
agent responses that the voice interface can speak.

Run with: uvicorn voice_api:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import os
from dotenv import load_dotenv
from elevenlabs import ElevenLabs
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize ElevenLabs client
elevenlabs_client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY")
)

from agents.intake_agent import IntakeAgent
from agents.base_agent import AgentState
from agents.crisis_agent import CrisisAgent
from agents.resource_agent import ResourceAgent
from models.mock_data import MOCK_THERAPISTS, therapist_db
from models.therapist import Therapist

app = FastAPI(title="MindBridge Voice API")

# Enable CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://mind-bridge-ftra.vercel.app",
        "https://*.vercel.app",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session storage (in production, use Redis or database)
sessions = {}


class VoiceRequest(BaseModel):
    """Voice message from user."""
    user_id: str
    message: str
    session_id: Optional[str] = None


class VoiceResponse(BaseModel):
    """Response to speak back to user."""
    response: str
    stage: str
    intake_complete: bool
    force_crisis: bool = False
    skip_privacy_prompt: bool = False


@app.post("/voice/intake", response_model=VoiceResponse)
async def process_voice_intake(request: VoiceRequest):
    """
    Process voice message through Intake Agent.

    Args:
        request: User's spoken message (transcribed)

    Returns:
        Agent's response to speak back + current stage
    """
    try:
        session_id = request.session_id or request.user_id

        # Get or create session
        if session_id not in sessions:
            sessions[session_id] = {
                "agent": IntakeAgent(),
                "state": AgentState(
                    user_id=request.user_id,
                    privacy_tier="full_support"
                )
            }

        session = sessions[session_id]
        agent = session["agent"]
        state = session["state"]

        # Add user message
        state = agent.add_message(state, "user", request.message)

        # Process through intake agent
        state = await agent.process(state)

        # Get response
        agent_response = state.messages[-1].content

        # Get current stage
        current_stage = state.agent_data.get("intake_stage", "greeting")

        # Check if intake complete
        intake_complete = agent.should_proceed_to_crisis_assessment(state)
        force_crisis = bool(state.agent_data.get("force_crisis", False))
        skip_privacy_prompt = bool(state.agent_data.get("skip_privacy_prompt", False))

        # Update session
        session["state"] = state

        # If intake complete, prepare for crisis assessment
        if intake_complete and session_id in sessions:
            # Add crisis agent to session
            sessions[session_id]["crisis_agent"] = CrisisAgent()

        return VoiceResponse(
            response=agent_response,
            stage=current_stage,
            intake_complete=intake_complete,
            force_crisis=force_crisis,
            skip_privacy_prompt=skip_privacy_prompt
        )

    except Exception as e:
        import traceback
        error_detail = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        print(f"ERROR in voice intake: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


@app.post("/therapist/licence-upload")
async def upload_licence(
    therapist_id: str = Query(..., alias="therapist-id"),
    file: UploadFile = File(...),
):
    """
    Upload a therapist licence file and save it under `uploads/`.

    Query:
    - therapist-id: the therapist's id (e.g., therapist_001)

    Form-Data:
    - file: the licence document (pdf, jpg, jpeg, png)
    """
    # Validate therapist exists
    therapist = therapist_db.get_therapist_by_id(therapist_id)
    if not therapist:
        raise HTTPException(status_code=404, detail="Therapist not found")

    # Basic content-type / extension whitelist
    allowed_ext = {".pdf", ".jpg", ".jpeg", ".png"}
    orig_name = os.path.basename(file.filename or "")
    _, ext = os.path.splitext(orig_name.lower())
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail="Unsupported file type. Allowed: pdf, jpg, jpeg, png")

    # Read file (size guard ~10MB)
    content = await file.read()
    size_bytes = len(content)
    max_bytes = 10 * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    # Ensure upload directories exist
    base_dir = os.path.join(os.getcwd(), "uploads")
    therapist_dir = os.path.join(base_dir, therapist_id)
    os.makedirs(therapist_dir, exist_ok=True)

    # Compose a unique filename
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    safe_name = orig_name if orig_name else f"licence{ext}"
    out_name = f"licence_{therapist_id}_{ts}{ext}"
    out_path = os.path.join(therapist_dir, out_name)

    # Write to disk
    try:
        with open(out_path, "wb") as f:
            f.write(content)
    finally:
        await file.close()

    # Return metadata
    rel_path = os.path.relpath(out_path, os.getcwd())
    return {
        "message": "Licence uploaded successfully",
        "therapist_id": therapist_id,
        "filename": out_name,
        "path": rel_path,
        "size_bytes": size_bytes,
    }


@app.post("/voice/crisis")
async def process_crisis_assessment(request: VoiceRequest):
    """Run crisis assessment after intake complete."""

    session_id = request.session_id or request.user_id

    if session_id not in sessions:
        return {"error": "No active session"}

    session = sessions[session_id]

    if "crisis_agent" not in session:
        return {"error": "Intake not complete"}

    crisis_agent = session["crisis_agent"]
    state = session["state"]

    # Run crisis assessment
    state = await crisis_agent.process(state)

    # Get response
    response = state.messages[-1].content

    # Update session
    session["state"] = state

    return {
        "response": response,
        "risk_level": state.agent_data.get("risk_level"),
        "crisis_detected": True  # Based on response analysis
    }


@app.post("/voice/tts")
async def text_to_speech(request: Request):
    """
    Convert text to speech using ElevenLabs API.
    Uses "Rachel" voice - a warm, empathetic female voice perfect for mental health support.
    """
    try:
        body = await request.json()
        text = body.get("text")
        if not text:
            raise HTTPException(status_code=400, detail="Text is required.")

        # Check if API key is configured
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not configured")

        # Generate audio with ElevenLabs v2 API
        # Using "Rachel" voice_id: 21m00Tcm4TlvDq8ikWAM - warm, empathetic female voice
        audio_generator = elevenlabs_client.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel - warm, empathetic female voice
            text=text,
            model_id="eleven_multilingual_v2"
        )

        # Convert generator to bytes
        audio_bytes = b''.join(audio_generator)

        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/mpeg"
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        print(f"TTS Error: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/therapists")
async def list_active_therapists():
    """Return all enrolled therapists with status 'active'."""
    all_therapists = therapist_db.get_all_therapists()
    active = [t for t in all_therapists]
    return {
        "count": len(active),
        "therapists": [t.model_dump() for t in active]
    }


class TherapistInput(BaseModel):
    """Permissive input model for therapist registration."""
    id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    specializations: Optional[List[str]] = None
    license_number: Optional[str] = None
    years_experience: Optional[int] = None
    time_slots: Optional[List[Dict[str, Any]]] = None
    is_volunteer: Optional[bool] = None
    status: Optional[str] = None
    max_patients: Optional[int] = None
    current_patients: Optional[int] = None
    bio: Optional[str] = None


def _generate_next_therapist_id() -> str:
    """Generate a new unique therapist id of the form therapist_XXX."""
    max_num = 0
    for t in MOCK_THERAPISTS:
        tid = str(t.get("id", ""))
        if tid.startswith("therapist_"):
            try:
                num = int(tid.split("_")[1])
                if num > max_num:
                    max_num = num
            except Exception:
                continue
    return f"therapist_{max_num + 1:03d}"


@app.post("/therapist")
async def register_therapist(input_data: TherapistInput):
    """
    Register a therapist and append to MOCK_THERAPISTS.

    - Fills missing fields with defaults or blanks.
    - Updates in-memory `therapist_db` for immediate availability.
    """
    # Build a normalized dict with defaults/blanks
    tdict: Dict[str, Any] = {}

    # Determine id and ensure uniqueness
    next_id = input_data.id or _generate_next_therapist_id()
    if any(str(t.get("id")) == str(next_id) for t in MOCK_THERAPISTS):
        next_id = _generate_next_therapist_id()
    tdict["id"] = next_id
    tdict["name"] = input_data.name or ""
    tdict["email"] = input_data.email or ""
    tdict["phone"] = input_data.phone or ""
    tdict["specializations"] = input_data.specializations or []
    tdict["license_number"] = input_data.license_number or ""
    tdict["years_experience"] = int(input_data.years_experience or 0)
    tdict["time_slots"] = input_data.time_slots or []
    tdict["is_volunteer"] = True if input_data.is_volunteer is None else bool(input_data.is_volunteer)
    tdict["status"] = input_data.status or "active"
    tdict["max_patients"] = int(input_data.max_patients or 10)
    tdict["current_patients"] = int(input_data.current_patients or 0)
    tdict["bio"] = input_data.bio or ""

    # Append to mock backing list
    MOCK_THERAPISTS.append(tdict)

    # Try to reflect in live in-memory DB (best-effort)
    # Ensure fields are acceptable for Therapist model
    try:
        # If email missing/blank, use a placeholder to satisfy EmailStr
        tdict_for_model = {**tdict}
        if not tdict_for_model.get("email"):
            tdict_for_model["email"] = f"{tdict_for_model['id']}@example.com"

        # Cast specializations to expected enum values (strings are fine for pydantic enums)
        therapist_obj = Therapist(**tdict_for_model)
        # Avoid duplicates
        if not therapist_db.get_therapist_by_id(therapist_obj.id):
            therapist_db.therapists.append(therapist_obj)
    except Exception as e:
        # Don't fail the API on validation errors for the in-memory DB
        print(f"Warning: Could not add therapist to in-memory DB: {e}")

    return {
        "message": "Therapist registered",
        "therapist": tdict,
        "count": len(MOCK_THERAPISTS),
    }


@app.get("/voice/session/{session_id}")
async def get_session_status(session_id: str):
    """Get current session status."""

    if session_id not in sessions:
        return {"exists": False}

    session = sessions[session_id]
    state = session["state"]

    return {
        "exists": True,
        "stage": state.agent_data.get("intake_stage"),
        "intake_complete": state.agent_data.get("intake_complete", False),
        "message_count": len(state.messages)
    }


@app.delete("/voice/session/{session_id}")
async def end_session(session_id: str):
    """End and cleanup session."""

    if session_id in sessions:
        del sessions[session_id]

    return {"message": "Session ended"}


@app.get("/debug/agent-init")
async def debug_agent_init():
    """Debug endpoint to test agent initialization."""
    try:
        # Try to initialize agent
        agent = IntakeAgent()
        return {
            "status": "success",
            "message": "Agent initialized successfully",
            "agent_type": type(agent).__name__,
            "has_llm": hasattr(agent, 'llm')
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
