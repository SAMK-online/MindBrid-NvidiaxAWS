"""
Session Model - Therapy session records
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# Session status tracking
class SessionStatus(str, Enum):
    SCHEDULED = "scheduled"        # Booked, not started
    IN_PROGRESS = "in_progress"    # Currently happening
    COMPLETED = "completed"        # Finished successfully
    CANCELLED = "cancelled"        # User cancelled
    NO_SHOW = "no_show"           # User didn't attend
    RESCHEDULED = "rescheduled"   # Moved to different time


# Session model
class Session(BaseModel):
    """Therapy session between user and therapist."""

    # Identification
    id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User in session")
    therapist_id: str = Field(..., description="Therapist conducting session")

    # Scheduling
    scheduled_time: datetime = Field(..., description="When session is scheduled")
    duration_minutes: int = Field(default=50, description="Session length")

    # Status
    status: SessionStatus = Field(
        default=SessionStatus.SCHEDULED,
        description="Current status"
    )

    # Session details
    session_type: str = Field(
        default="individual",
        description="individual, group, crisis, follow_up"
    )
    focus_areas: List[str] = Field(
        default_factory=list,
        description="Topics covered (e.g., anxiety, relationships)"
    )

    # Notes (privacy-controlled)
    therapist_notes: Optional[str] = Field(
        None,
        description="Therapist's private notes"
    )
    # Only visible to therapist unless user is FULL_SUPPORT tier

    homework_assigned: List[str] = Field(
        default_factory=list,
        description="List of homework tasks (becomes Habits)"
    )

    # Timing
    start_time: Optional[datetime] = Field(
        None,
        description="When session actually started"
    )
    end_time: Optional[datetime] = Field(
        None,
        description="When session actually ended"
    )

    # Follow-up
    follow_up_scheduled: bool = Field(
        default=False,
        description="Whether next session is booked"
    )
    next_session_id: Optional[str] = Field(
        None,
        description="ID of next scheduled session"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When session was created/scheduled"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "session_001",
                "user_id": "user_001",
                "therapist_id": "therapist_001",
                "scheduled_time": "2025-10-27T14:00:00",
                "duration_minutes": 50,
                "status": "completed",
                "session_type": "individual",
                "focus_areas": ["anxiety", "coping_strategies"],
                "homework_assigned": ["Meditate 10 min daily", "Journal before bed"]
            }
        }
