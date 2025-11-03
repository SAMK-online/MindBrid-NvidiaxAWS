"""
MindBridge AI - Workflow Orchestration
=======================================
LangGraph workflows for multi-agent coordination.

Workflows:
- crisis_to_resource: Crisis assessment → Resource matching flow
- full_support: Complete user journey (crisis → resource → habit)
"""

from .crisis_to_resource import create_crisis_resource_workflow

__all__ = ["create_crisis_resource_workflow"]
