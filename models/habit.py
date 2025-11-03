"""
Habit Model - Therapeutic homework and habit tracking
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from datetime import date as date_type
from enum import Enum
from pydantic import BaseModel, Field


# How often the habit should be performed
class HabitFrequency(str, Enum):
    DAILY = "daily"                    # Every day
    WEEKDAYS = "weekdays"              # Monday-Friday
    WEEKENDS = "weekends"              # Saturday-Sunday
    WEEKLY = "weekly"                  # Once per week
    CUSTOM = "custom"                  # Custom schedule


# Current status of the habit
class HabitStatus(str, Enum):
    ACTIVE = "active"                  # Currently tracking
    PAUSED = "paused"                  # Temporarily paused
    COMPLETED = "completed"            # Goal achieved
    ABANDONED = "abandoned"            # User stopped


# Individual completion record
class HabitCompletion(BaseModel):
    """Single completion record for a habit."""

    date: date_type = Field(..., description="When completed")
    completed: bool = Field(..., description="Whether completed")
    notes: Optional[str] = Field(None, description="User notes")
    reminded: bool = Field(default=False, description="Whether agent reminded user")


# Main habit model
class Habit(BaseModel):
    """Therapeutic homework assigned by therapist and tracked by Habit Agent."""

    # Identification
    id: str = Field(..., description="Unique habit identifier")
    user_id: str = Field(..., description="User this habit belongs to")

    # Habit details
    name: str = Field(..., description="What to do (e.g., 'Meditate 10 minutes')")
    description: Optional[str] = Field(
        None,
        description="Detailed description or instructions"
    )

    # Frequency and duration
    frequency: HabitFrequency = Field(
        default=HabitFrequency.DAILY,
        description="How often to perform"
    )
    duration_minutes: Optional[int] = Field(
        None,
        ge=1,
        description="How long the activity takes"
    )
    target_days: int = Field(
        default=30,
        ge=1,
        description="How many days to track (e.g., 30-day challenge)"
    )

    # Status
    status: HabitStatus = Field(
        default=HabitStatus.ACTIVE,
        description="Current status"
    )

    # Tracking
    start_date: date_type = Field(
        default_factory=date_type.today,
        description="When tracking started"
    )
    end_date: Optional[date_type] = Field(
        None,
        description="When tracking ends (if applicable)"
    )

    completions: List[HabitCompletion] = Field(
        default_factory=list,
        description="Completion history"
    )

    # Habit Agent settings
    reminder_time: Optional[str] = Field(
        None,
        description="When to remind (HH:MM format)"
    )
    auto_check_enabled: bool = Field(
        default=True,
        description="Whether Habit Agent monitors autonomously"
    )

    # Adaptive difficulty
    difficulty_level: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Current difficulty (1=easy, 5=hard)"
    )
    # Agent can adjust this based on success rate

    # Metadata
    created_by: str = Field(
        default="user",
        description="Who created: 'user', 'therapist', 'agent'"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When created"
    )
    last_completed: Optional[datetime] = Field(
        None,
        description="Last successful completion"
    )

    # Computed properties
    @property
    def completion_rate(self) -> float:
        """Calculate percentage of days completed."""
        if not self.completions:
            return 0.0

        completed_count = sum(1 for c in self.completions if c.completed)
        return (completed_count / len(self.completions)) * 100

    @property
    def current_streak(self) -> int:
        """Calculate current consecutive completion streak."""
        if not self.completions:
            return 0

        # Sort by date (newest first)
        sorted_completions = sorted(
            self.completions,
            key=lambda x: x.date,
            reverse=True
        )

        streak = 0
        for completion in sorted_completions:
            if completion.completed:
                streak += 1
            else:
                break

        return streak

    @property
    def days_active(self) -> int:
        """How many days has this habit been tracked."""
        return (date_type.today() - self.start_date).days

    class Config:
        json_schema_extra = {
            "example": {
                "id": "habit_001",
                "user_id": "user_001",
                "name": "Meditate for 10 minutes",
                "frequency": "daily",
                "duration_minutes": 10,
                "target_days": 30,
                "status": "active",
                "reminder_time": "09:00",
                "auto_check_enabled": True,
                "difficulty_level": 1,
                "created_by": "therapist"
            }
        }
