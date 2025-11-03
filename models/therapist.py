"""
Therapist Model - Volunteer therapist profiles and availability
"""

from typing import List, Optional
from datetime import datetime, time
from enum import Enum
from pydantic import BaseModel, Field, EmailStr


# Therapist specializations - what issues they can help with
class TherapistSpecialization(str, Enum):
    ANXIETY = "anxiety"
    DEPRESSION = "depression"
    TRAUMA = "trauma"
    ADDICTION = "addiction"
    RELATIONSHIPS = "relationships"
    GRIEF = "grief"
    EATING_DISORDERS = "eating_disorders"
    OCD = "ocd"
    PTSD = "ptsd"
    GENERAL = "general"


# Available time slots for therapy sessions
class TimeSlot(BaseModel):
    """Represents an available time slot for therapy sessions."""

    day_of_week: str  # "Monday", "Tuesday", etc.
    start_time: str   # "09:00" (24-hour format)
    end_time: str     # "17:00"
    timezone: str = "America/New_York"

    # Metadata
    is_available: bool = True
    recurring: bool = True  # If true, available every week

    class Config:
        # Example for documentation
        json_schema_extra = {
            "example": {
                "day_of_week": "Monday",
                "start_time": "14:00",
                "end_time": "16:00",
                "timezone": "America/New_York",
                "is_available": True,
                "recurring": True
            }
        }


# Main therapist model
class Therapist(BaseModel):
    """Volunteer therapist profile with availability and specializations."""

    # Identification
    id: str = Field(..., description="Unique therapist identifier")
    name: str = Field(..., description="Full name")

    # Contact
    email: EmailStr = Field(..., description="Contact email")
    phone: Optional[str] = Field(None, description="Phone number (optional)")

    # Professional info
    specializations: List[TherapistSpecialization] = Field(
        default_factory=list,
        description="Areas of expertise"
    )
    license_number: Optional[str] = Field(None, description="Professional license")
    years_experience: int = Field(..., ge=0, description="Years of experience")

    # Availability
    time_slots: List[TimeSlot] = Field(
        default_factory=list,
        description="Available time slots for sessions"
    )

    # Status
    is_volunteer: bool = Field(True, description="Volunteer vs paid therapist")
    status: str = Field(
        default="active",
        description="active, pending, offline, full"
    )

    # Capacity
    max_patients: int = Field(default=10, description="Maximum concurrent patients")
    current_patients: int = Field(default=0, description="Current patient count")

    # Bio
    bio: Optional[str] = Field(
        None,
        max_length=500,
        description="Short bio (shown to users)"
    )

    # Metadata
    joined_date: datetime = Field(
        default_factory=datetime.now,
        description="When therapist joined platform"
    )
    last_active: datetime = Field(
        default_factory=datetime.now,
        description="Last activity timestamp"
    )

    # Computed properties
    @property
    def is_available(self) -> bool:
        """Check if therapist can take new patients."""
        return (
            self.status == "active" and
            self.current_patients < self.max_patients and
            len(self.time_slots) > 0
        )

    @property
    def availability_percentage(self) -> float:
        """Calculate how full the therapist's schedule is."""
        if self.max_patients == 0:
            return 0.0
        return (self.current_patients / self.max_patients) * 100

    class Config:
        # Example for documentation
        json_schema_extra = {
            "example": {
                "id": "therapist_001",
                "name": "Dr. Sarah Johnson",
                "email": "sarah.johnson@mindbridge.org",
                "specializations": ["anxiety", "depression"],
                "years_experience": 8,
                "is_volunteer": True,
                "status": "active",
                "max_patients": 10,
                "current_patients": 3,
                "bio": "Licensed psychologist specializing in anxiety and depression..."
            }
        }
