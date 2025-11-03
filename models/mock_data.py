"""
Mock Database - 10 Realistic Therapists for Demo
=================================================

This creates a realistic therapist database for the hackathon demo.
In production, this would be a real Supabase database.

For the demo, we use in-memory storage with JSON persistence.
"""

from typing import List, Optional, Dict
from datetime import datetime
import json
import os

from models.therapist import Therapist, TimeSlot, TherapistSpecialization


# 10 realistic volunteer therapists with varied specializations and availability
MOCK_THERAPISTS: List[Dict] = [
    {
        "id": "therapist_001",
        "name": "Dr. Sarah Johnson",
        "email": "sarah.johnson@mindbridge.org",
        "phone": "+1-555-0101",
        "specializations": ["anxiety", "depression", "trauma"],
        "license_number": "PSY-12345-NY",
        "years_experience": 12,
        "time_slots": [
            {"day_of_week": "Monday", "start_time": "09:00", "end_time": "17:00"},
            {"day_of_week": "Wednesday", "start_time": "09:00", "end_time": "17:00"},
            {"day_of_week": "Friday", "start_time": "13:00", "end_time": "18:00"},
        ],
        "is_volunteer": True,
        "status": "active",
        "max_patients": 12,
        "current_patients": 3,
        "bio": "Licensed clinical psychologist with 12 years of experience specializing in trauma-informed care and evidence-based treatments for anxiety and depression."
    },
    {
        "id": "therapist_002",
        "name": "Dr. Michael Chen",
        "email": "michael.chen@mindbridge.org",
        "phone": "+1-555-0102",
        "specializations": ["addiction", "relationships", "general"],
        "license_number": "LMFT-67890-CA",
        "years_experience": 8,
        "time_slots": [
            {"day_of_week": "Tuesday", "start_time": "10:00", "end_time": "18:00"},
            {"day_of_week": "Thursday", "start_time": "10:00", "end_time": "18:00"},
        ],
        "is_volunteer": True,
        "status": "active",
        "max_patients": 10,
        "current_patients": 7,
        "bio": "Marriage and family therapist focusing on addiction recovery and relationship counseling using cognitive-behavioral approaches."
    },
    {
        "id": "therapist_003",
        "name": "Dr. Emily Rodriguez",
        "email": "emily.rodriguez@mindbridge.org",
        "phone": "+1-555-0103",
        "specializations": ["eating_disorders", "anxiety", "depression"],
        "license_number": "PSY-34567-TX",
        "years_experience": 15,
        "time_slots": [
            {"day_of_week": "Monday", "start_time": "08:00", "end_time": "12:00"},
            {"day_of_week": "Wednesday", "start_time": "14:00", "end_time": "19:00"},
            {"day_of_week": "Saturday", "start_time": "09:00", "end_time": "13:00"},
        ],
        "is_volunteer": True,
        "status": "active",
        "max_patients": 15,
        "current_patients": 10,
        "bio": "Specialized in eating disorders with extensive experience in body image issues, anxiety, and depression. Uses dialectical behavior therapy (DBT) and acceptance-based approaches."
    },
    {
        "id": "therapist_004",
        "name": "Dr. James Williams",
        "email": "james.williams@mindbridge.org",
        "phone": "+1-555-0104",
        "specializations": ["ptsd", "trauma", "grief"],
        "license_number": "LCSW-45678-IL",
        "years_experience": 20,
        "time_slots": [
            {"day_of_week": "Tuesday", "start_time": "09:00", "end_time": "15:00"},
            {"day_of_week": "Thursday", "start_time": "09:00", "end_time": "15:00"},
        ],
        "is_volunteer": True,
        "status": "active",
        "max_patients": 8,
        "current_patients": 8,  # FULL - for demo showing fallback
        "bio": "Veteran affairs specialist with 20 years treating PTSD and trauma. Certified in EMDR therapy and prolonged exposure therapy."
    },
    {
        "id": "therapist_005",
        "name": "Dr. Lisa Thompson",
        "email": "lisa.thompson@mindbridge.org",
        "phone": "+1-555-0105",
        "specializations": ["anxiety", "ocd", "general"],
        "license_number": "PSY-56789-FL",
        "years_experience": 10,
        "time_slots": [
            {"day_of_week": "Monday", "start_time": "13:00", "end_time": "20:00"},
            {"day_of_week": "Friday", "start_time": "09:00", "end_time": "16:00"},
        ],
        "is_volunteer": True,
        "status": "active",
        "max_patients": 12,
        "current_patients": 5,
        "bio": "Specialist in anxiety disorders and OCD using exposure and response prevention (ERP) therapy. Passionate about making mental health care accessible."
    },
    {
        "id": "therapist_006",
        "name": "Dr. David Martinez",
        "email": "david.martinez@mindbridge.org",
        "phone": "+1-555-0106",
        "specializations": ["depression", "grief", "general"],
        "license_number": "LMHC-67891-MA",
        "years_experience": 6,
        "time_slots": [
            {"day_of_week": "Wednesday", "start_time": "10:00", "end_time": "18:00"},
            {"day_of_week": "Saturday", "start_time": "10:00", "end_time": "14:00"},
        ],
        "is_volunteer": True,
        "status": "active",
        "max_patients": 10,
        "current_patients": 4,
        "bio": "Mental health counselor specializing in depression and grief counseling. Uses person-centered and existential therapy approaches."
    },
    {
        "id": "therapist_007",
        "name": "Dr. Amanda Foster",
        "email": "amanda.foster@mindbridge.org",
        "phone": "+1-555-0107",
        "specializations": ["relationships", "anxiety", "general"],
        "license_number": "LMFT-78912-WA",
        "years_experience": 9,
        "time_slots": [
            {"day_of_week": "Tuesday", "start_time": "14:00", "end_time": "21:00"},
            {"day_of_week": "Thursday", "start_time": "14:00", "end_time": "21:00"},
        ],
        "is_volunteer": True,
        "status": "active",
        "max_patients": 10,
        "current_patients": 6,
        "bio": "Couples and individual therapist focusing on communication, attachment, and relationship dynamics. Gottman Method certified."
    },
    {
        "id": "therapist_008",
        "name": "Dr. Robert Kim",
        "email": "robert.kim@mindbridge.org",
        "phone": "+1-555-0108",
        "specializations": ["addiction", "depression", "trauma"],
        "license_number": "LCSW-89123-OR",
        "years_experience": 14,
        "time_slots": [
            {"day_of_week": "Monday", "start_time": "11:00", "end_time": "19:00"},
            {"day_of_week": "Wednesday", "start_time": "11:00", "end_time": "19:00"},
        ],
        "is_volunteer": True,
        "status": "offline",  # OFFLINE - for demo showing search fallback
        "max_patients": 12,
        "current_patients": 0,
        "bio": "Addiction counselor with dual specialization in trauma and depression. 14 years helping individuals achieve lasting recovery."
    },
    {
        "id": "therapist_009",
        "name": "Dr. Jennifer Lee",
        "email": "jennifer.lee@mindbridge.org",
        "phone": "+1-555-0109",
        "specializations": ["anxiety", "depression", "general"],
        "license_number": "PSY-91234-CO",
        "years_experience": 7,
        "time_slots": [
            {"day_of_week": "Monday", "start_time": "09:00", "end_time": "17:00"},
            {"day_of_week": "Tuesday", "start_time": "09:00", "end_time": "17:00"},
            {"day_of_week": "Thursday", "start_time": "09:00", "end_time": "13:00"},
        ],
        "is_volunteer": True,
        "status": "active",
        "max_patients": 15,
        "current_patients": 2,
        "bio": "Clinical psychologist offering evidence-based treatment for anxiety and depression. Specializes in young adults and life transitions."
    },
    {
        "id": "therapist_010",
        "name": "Dr. Patricia Brown",
        "email": "patricia.brown@mindbridge.org",
        "phone": "+1-555-0110",
        "specializations": ["grief", "trauma", "depression"],
        "license_number": "LMHC-12345-NC",
        "years_experience": 18,
        "time_slots": [
            {"day_of_week": "Wednesday", "start_time": "08:00", "end_time": "16:00"},
            {"day_of_week": "Friday", "start_time": "08:00", "end_time": "16:00"},
        ],
        "is_volunteer": True,
        "status": "active",
        "max_patients": 10,
        "current_patients": 9,
        "bio": "Grief counselor and trauma specialist with 18 years of experience helping individuals navigate loss and develop resilience."
    }
]


# In-memory database (for demo - in production this would be Supabase)
class TherapistDatabase:
    """
    Simple in-memory database for therapists.

    For the hackathon demo, this is perfect.
    For production, replace with Supabase client.
    """

    def __init__(self):
        # Load therapists into Pydantic models for validation
        self.therapists: List[Therapist] = [
            Therapist(**therapist_data)
            for therapist_data in MOCK_THERAPISTS
        ]

        print(f"✅ Loaded {len(self.therapists)} therapists into database")

    def get_all_therapists(self) -> List[Therapist]:
        """Get all therapists."""
        return self.therapists

    def get_available_therapists(
        self,
        specialization: Optional[TherapistSpecialization] = None
    ) -> List[Therapist]:
        """
        Get therapists who are available (not full, active status).

        Args:
            specialization: Filter by specialization if provided

        Returns:
            List of available therapists
        """
        available = [
            t for t in self.therapists
            if t.is_available  # Uses the @property we defined
        ]

        # Filter by specialization if requested
        if specialization:
            available = [
                t for t in available
                if specialization in t.specializations
            ]

        return available

    def get_therapist_by_id(self, therapist_id: str) -> Optional[Therapist]:
        """Get specific therapist by ID."""
        for therapist in self.therapists:
            if therapist.id == therapist_id:
                return therapist
        return None

    def book_therapist(self, therapist_id: str) -> bool:
        """
        Book a therapist (increment their patient count).

        Returns:
            True if successful, False if therapist is full
        """
        therapist = self.get_therapist_by_id(therapist_id)

        if not therapist or not therapist.is_available:
            return False

        therapist.current_patients += 1
        therapist.last_active = datetime.now()

        return True

    def add_therapist(self, therapist: Therapist) -> bool:
        """
        Add a new therapist to database.

        This is called by Resource Agent when it finds new therapists!
        """
        # Check if already exists
        if self.get_therapist_by_id(therapist.id):
            return False

        self.therapists.append(therapist)
        print(f"✅ Added new therapist: {therapist.name}")

        return True

    def get_statistics(self) -> Dict:
        """Get database statistics for monitoring."""
        total = len(self.therapists)
        active = len([t for t in self.therapists if t.status == "active"])
        available = len(self.get_available_therapists())
        full = len([t for t in self.therapists if t.current_patients >= t.max_patients])

        return {
            "total_therapists": total,
            "active": active,
            "available": available,
            "full": full,
            "utilization_rate": ((total - available) / total * 100) if total > 0 else 0
        }


# Create global database instance
# In production, this would be a Supabase client
therapist_db = TherapistDatabase()


# Helper function to export data (useful for debugging)
def export_to_json(filename: str = "therapist_database.json"):
    """Export therapist database to JSON file."""
    data = [t.model_dump() for t in therapist_db.get_all_therapists()]

    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"✅ Exported {len(data)} therapists to {filename}")


# Example usage
if __name__ == "__main__":
    # Test the database
    print("=" * 70)
    print("🗄️  Therapist Database Test")
    print("=" * 70)
    print()

    # Get statistics
    stats = therapist_db.get_statistics()
    print("📊 Database Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # Get available therapists
    available = therapist_db.get_available_therapists()
    print(f"✅ Available Therapists: {len(available)}")
    for therapist in available[:3]:  # Show first 3
        print(f"   • {therapist.name} - {', '.join(therapist.specializations)}")
    print()

    # Get therapists by specialization
    anxiety_therapists = therapist_db.get_available_therapists(
        specialization=TherapistSpecialization.ANXIETY
    )
    print(f"🧠 Anxiety Specialists Available: {len(anxiety_therapists)}")
    for therapist in anxiety_therapists:
        print(f"   • {therapist.name} ({therapist.current_patients}/{therapist.max_patients} patients)")
    print()

    # Export to JSON
    export_to_json()
