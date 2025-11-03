"""
User Model - User profiles with privacy tier control
"""

from typing import Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, EmailStr


# Privacy tiers - how much AI assistance user allows
class PrivacyTier(str, Enum):
    """
    Privacy tiers control how much AI involvement the user allows.

    This is a KEY differentiator for MindBridge - user controls their data!
    """

    NO_RECORDS = "no_records"
    # No data stored, complete anonymity
    # Use case: User just wants crisis support, no tracking

    YOUR_PRIVATE_NOTES = "your_private_notes"
    # User-encrypted data only, AI can't access historical patterns
    # Use case: User wants to track habits but keep data private

    ASSISTED_HANDOFF = "assisted_handoff"
    # Platform can help with therapist transitions
    # Use case: User wants smooth handoffs between therapists

    FULL_SUPPORT = "full_support"
    # Complete AI assistance and insights
    # Use case: User wants maximum AI help (habit tracking, insights, etc.)


# Main user model
class User(BaseModel):
    """User profile with privacy controls."""

    # Identification
    id: str = Field(..., description="Unique user identifier")
    email: Optional[EmailStr] = Field(None, description="Email (optional based on privacy)")

    # Privacy settings
    privacy_tier: PrivacyTier = Field(
        default=PrivacyTier.YOUR_PRIVATE_NOTES,
        description="Level of AI assistance allowed"
    )

    # Demographics (optional based on privacy tier)
    age: Optional[int] = Field(None, ge=13, le=120, description="Age")
    location: Optional[str] = Field(None, description="City/State for resource matching")
    timezone: str = Field(default="America/New_York", description="User timezone")

    # Status
    is_active: bool = Field(default=True, description="Account active status")
    in_crisis: bool = Field(default=False, description="Currently in crisis flag")

    # Therapist matching
    matched_therapist_id: Optional[str] = Field(
        None,
        description="Currently matched therapist"
    )
    awaiting_match: bool = Field(
        default=False,
        description="Waiting for therapist match"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Account creation date"
    )
    last_active: datetime = Field(
        default_factory=datetime.now,
        description="Last activity"
    )

    # Consent flags
    consented_to_data_collection: bool = Field(
        default=False,
        description="Explicitly consented to data collection"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "user_001",
                "email": "user@example.com",
                "privacy_tier": "full_support",
                "age": 28,
                "location": "New York, NY",
                "is_active": True,
                "in_crisis": False
            }
        }
