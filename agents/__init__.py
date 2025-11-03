"""
MindBridge AI - Agent Package
==============================
This package contains all autonomous agents for the mental health support platform.

Agent Architecture:
- BaseAgent: Foundation class with shared functionality
- CrisisAgent: Assesses urgency and risk using ReAct pattern
- HabitAgent: Autonomous therapeutic homework monitoring
- ResourceAgent: Matches users with therapists
- CoordinatorAgent: Orchestrates all agents via LangGraph
"""

from .base_agent import BaseAgent
from .coordinator_agent import CoordinatorAgent
from .crisis_agent import CrisisAgent
from .habit_agent import HabitAgent
from .resource_agent import ResourceAgent

__all__ = [
    "BaseAgent",
    "CoordinatorAgent",
    "CrisisAgent",
    "HabitAgent",
    "ResourceAgent",
]
