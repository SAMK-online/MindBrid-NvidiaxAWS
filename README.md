# MindBridge — NVIDIA × AWS Edition

> Democratizing mental-health support with autonomous, AWS-hosted NIM agents.

## 🎯 Mission
Millions struggle to access professional mental-health support because of cost, availability, or stigma. MindBridge pairs those users with volunteer therapists and compassionate AI guidance from **Nima**, an NVIDIA Nemotron–powered agent that triages, matches, and supports people end-to-end.

## 🎬 Demo
MindBridge autonomous intake → crisis triage → therapist match workflow: *(attach `MindBridgeDemo.mp4` when submitting to Devpost/GitHub releases).*

## ✨ Why Nima Feels Different
- 🤝 **Intelligent Therapist Matching** – Searches the volunteer roster, recruits new therapists, and recommends time slots automatically.
- 🚨 **Instant Crisis Detection** – LangGraph-driven ReAct loop flags risk phrases and escalates to crisis protocols within a turn.
- 💬 **Empathetic Intake** – Stage-aware dialogue flow that builds trust before assessments.
- 📈 **Adaptive Habit Tracking** – Generates micro-habits, tracks streaks, and nudges based on context.
- 🔒 **Privacy Tiers** – Users decide how much information MindBridge stores (No Records → Full Support).

## 🏗️ Multi-Agent Architecture
```
┌─────────────────────────────────────────────┐
│     Coordinator Agent (Nemotron 8B)         │
└────────────┬────────────────────────────────┘
             │
    ┌────────┼────────┬───────────┬──────────┐
    ▼        ▼        ▼           ▼          ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
│Intake  ││Crisis  ││Resource││Habit   ││Quality │
│Agent   ││Agent   ││Agent   ││Agent   ││Monitor │
└────────┘└────────┘└────────┘└────────┘└────────┘
```

| Agent | Model | Purpose |
|-------|-------|---------|
| **Coordinator** | Nemotron 8B | Chooses the next specialist, writes plan steps |
| **Intake** | Nemotron 8B | Warm, staged conversation to gather context |
| **Crisis** | Nemotron 8B | ReAct risk assessment, emergency escalation |
| **Resource** | Nemotron 8B + Embeddings | RAG-first therapist/resource search |
| **Habit** | Nemotron 8B | Personalized micro-habits, streak tracking |
| **Quality Monitor** | Nemotron 8B | (Optional) evaluates response quality |

## 🚀 Tech Stack
- **Backend**: FastAPI, LangGraph, Python 3.11
- **Frontend**: React 19, Vite, Tailwind CSS, React Router
- **NVIDIA NIM**:  
  - `nvidia-nemotron-nano-8b-nim` (reasoning)  
  - `nvidia-llama3-2-nv-embedqa-1b-v2-nim` (retrieval embeddings)
- **AWS**: SageMaker JumpStart endpoints (optionally S3 + FAISS/pgvector for vector store)
- **Integrations**: Tavily (web search fallback), ElevenLabs (voice synthesis), Supabase/Redis (optional persistence)

## 📦 Project Structure
```
agents/        # Base + specialist agents sharing the NIM client
api/index.py   # Vercel adapter for FastAPI
models/        # Pydantic schemas + mock data helpers
voice_api.py   # FastAPI voice/chat entrypoint
workflows/     # LangGraph graphs (intake→crisis→resource, etc.)
ui/            # React frontend (chat, scheduling, habits dashboard)
deploy_nim_sagemaker.py  # One-click JumpStart deployment script
.env.example   # AWS/NIM/Tavily configuration template
```

---

## 🧭 Hackathon Deployment Guide (AWS SageMaker)

### 1. Get the Vocareum lab credentials
From the hackathon dashboard copy:
```
aws_access_key_id=...
aws_secret_access_key=...
aws_session_token=...
```

### 2. Launch the deployment script
In the Vocareum terminal:
```bash
git clone https://github.com/SAMK-online/MindBrid-NvidiaxAWS.git
cd MindBrid-NvidiaxAWS

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade boto3 sagemaker

export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="..."
export AWS_DEFAULT_REGION="us-east-1"
export SAGEMAKER_EXECUTION_ROLE="arn:aws:iam::112571254920:role/voclabs"

python deploy_nim_sagemaker.py
cat nim_endpoints.json
```
The script resolves the latest JumpStart versions, deploys both endpoints (LLM & embeddings), and saves `nim_endpoints.json`. Download or copy the JSON for later.

### 3. Configure the application
Create `.env` locally with the SageMaker endpoint names:
```env
AWS_REGION=us-east-1
NIM_LLM_ENDPOINT=<nemotron-endpoint-name>
NIM_EMBED_ENDPOINT=<embedding-endpoint-name>
# If not using an AWS profile locally:
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_SESSION_TOKEN=...
TAVILY_API_KEY=<optional>
ELEVENLABS_API_KEY=<optional>
```
Frontend (`ui/.env`):
```env
VITE_API_URL=http://localhost:8000
```

### 4. Run MindBridge locally
```bash
# backend
pip install -r requirements.txt
uvicorn voice_api:app --reload --port 8000

# frontend
cd ui
npm install
npm run dev
```
Visit http://localhost:5173 to interact with Nima. All agent calls now route through the SageMaker NIM endpoints.

### 5. Optional retrieval store
- Use the embedding endpoint to vectorize therapist bios / resource snippets.
- Store vectors in FAISS/pgvector and expose a retrieval tool invoked by `ResourceAgent` before Tavily fallback.
- Document any additional data sources in your submission.

---

## 🛠️ Dev & Deployment Notes
- `voice_api.py` is ready for containerized deployment (Procfile included).
- `api/index.py` adapts FastAPI for Vercel serverless if you need a quick demo backend.
- Log output (`loguru`) records agent decisions for judging / debugging.
- Remember to shut down SageMaker endpoints when not in use to preserve the $100 AWS credit.

## 🤝 Contributing / Submission Tips
1. Highlight the AWS integration (screenshots of SageMaker console, `nim_endpoints.json`, CloudWatch logs).
2. Capture a short demo (screen + voice) showing intake, crisis detection, matching, and habit follow-up.
3. Note that Tavily/ElevenLabs keys require their own terms-of-use compliance.
4. For feature tweaks, branch off `main`, push, and submit PRs (standard GitHub flow).

Good luck at the NVIDIA × AWS Agentic AI hackathon—go show what Nima can do! 💚
