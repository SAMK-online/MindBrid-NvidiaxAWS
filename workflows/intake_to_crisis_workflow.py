"""
Intake → Crisis → Resource Workflow
====================================

ENHANCED workflow with warm, conversational intake first.

NEW FLOW:
1. Intake Agent: Friendly conversation (hi → how are you → what brings you → explore)
2. Crisis Agent: Assess risk level
3. IF high/moderate risk → Resource Agent finds therapist
4. IF low/none risk → Support resources
5. Return final response

This creates a HUMAN-LIKE experience:
- No rushing to assessment
- Builds trust first
- Gathers information naturally
- Then provides appropriate support
"""

from typing import TypedDict, Literal, Annotated, Optional, Dict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage
from loguru import logger

from agents.coordinator_agent import CoordinatorAgent
from agents.intake_agent import IntakeAgent
from agents.crisis_agent import CrisisAgent
from agents.resource_agent import ResourceAgent
from agents.habit_agent import HabitAgent
from agents.base_agent import AgentState


# ================================================================
# WORKFLOW STATE
# ================================================================

class WorkflowState(TypedDict):
    """
    State that flows through the entire workflow.

    Now includes intake stage tracking!
    """

    # Conversation messages
    messages: Annotated[list[BaseMessage], add_messages]

    # User information
    user_id: str
    privacy_tier: str

    # Intake stage tracking
    intake_complete: bool
    intake_stage: Optional[str]

    # Coordinator plan
    coordinator_plan: Optional[list[str]]
    needs_habit_support: bool
    habit_plan_created: bool
    habit_plan: Optional[list[Dict[str, str]]]

    # Crisis assessment results
    risk_level: Optional[str]
    crisis_detected: bool

    # Resource matching results
    therapist_matched: bool
    matched_therapist_id: Optional[str]
    matched_therapist_name: Optional[str]

    # Workflow control
    next_step: Optional[str]
    workflow_complete: bool


# ================================================================
# AGENT NODE FUNCTIONS
# ================================================================


async def coordinator_node(state: WorkflowState) -> WorkflowState:
    """
    Coordinator Node - Decides which specialists engage first.

    This makes the orchestration explicit: the Coordinator inspects the
    most recent user message, determines whether to start with Intake or
    Crisis Agent, and flags whether Habit Agent should follow later.
    """

    logger.info("=" * 70)
    logger.info("🎯 WORKFLOW: Coordinator evaluating next steps")
    logger.info("=" * 70)

    coordinator = CoordinatorAgent()
    agent_state = AgentState(
        messages=state["messages"],
        user_id=state["user_id"],
        privacy_tier=state["privacy_tier"]
    )

    agent_state = await coordinator.process(agent_state)

    initial_route = agent_state.agent_data.get("initial_route", "intake")
    needs_habit_support = agent_state.agent_data.get("needs_habit_support", False)
    plan_steps = agent_state.agent_data.get("coordinator_plan", [])

    logger.info(
        "🧭 Coordinator route decided",
        extra={
            "initial_route": initial_route,
            "needs_habit_support": needs_habit_support,
            "plan": plan_steps
        }
    )

    return {
        **state,
        "messages": agent_state.messages,
        "next_step": initial_route,
        "needs_habit_support": needs_habit_support,
        "coordinator_plan": plan_steps,
    }


async def intake_node(state: WorkflowState) -> WorkflowState:
    """
    Intake Node - Friendly conversational onboarding.

    This node:
    1. Greets warmly
    2. Asks how they're doing
    3. Asks what brings them here
    4. Explores what's troubling them
    5. Gathers context naturally
    6. Marks intake complete when ready
    """

    logger.info("=" * 70)
    logger.info("🤝 WORKFLOW: Intake Conversation Starting")
    logger.info("=" * 70)

    # Create Intake Agent
    intake_agent = IntakeAgent()

    # Convert workflow state to agent state
    agent_state = AgentState(
        messages=state["messages"],
        user_id=state["user_id"],
        privacy_tier=state["privacy_tier"]
    )

    # Add intake stage from workflow state
    if state.get("intake_stage"):
        agent_state.agent_data["intake_stage"] = state["intake_stage"]

    # Run Intake Agent
    agent_state = await intake_agent.process(agent_state)

    # Check if intake is complete
    intake_complete = intake_agent.should_proceed_to_crisis_assessment(agent_state)

    logger.info(f"🎯 Intake Status: {'Complete ✅' if intake_complete else 'Ongoing 🔄'}")

    # Update workflow state
    return {
        **state,
        "messages": agent_state.messages,
        "intake_complete": intake_complete,
        "intake_stage": agent_state.agent_data.get("intake_stage"),
        "next_step": "crisis_assessment" if intake_complete else "intake"
    }


async def crisis_assessment_node(state: WorkflowState) -> WorkflowState:
    """
    Crisis Assessment Node - Analyzes gathered information.

    This runs AFTER intake is complete, using all the context
    gathered during the friendly conversation.
    """

    logger.info("=" * 70)
    logger.info("🚨 WORKFLOW: Crisis Assessment Starting")
    logger.info("=" * 70)

    # Create Crisis Agent
    crisis_agent = CrisisAgent()

    # Convert workflow state to agent state
    agent_state = AgentState(
        messages=state["messages"],
        user_id=state["user_id"],
        privacy_tier=state["privacy_tier"]
    )

    # Run Crisis Agent (this does ReAct assessment)
    agent_state = await crisis_agent.process(agent_state)

    # Extract crisis level from agent's analysis
    response_text = agent_state.messages[-1].content.lower() if agent_state.messages else ""

    # Simple risk detection (in production, would be more sophisticated)
    if any(word in response_text for word in ["immediate", "emergency", "911"]):
        risk_level = "immediate"
        crisis_detected = True
    elif any(word in response_text for word in ["high priority", "therapist", "connect you"]):
        risk_level = "high"
        crisis_detected = True
    elif any(word in response_text for word in ["moderate", "check-in", "follow up"]):
        risk_level = "moderate"
        crisis_detected = True
    elif any(word in response_text for word in ["low", "stressed", "support"]):
        risk_level = "low"
        crisis_detected = False
    else:
        risk_level = "none"
        crisis_detected = False

    logger.info(f"🎯 Crisis Assessment Complete: Risk Level = {risk_level}")

    # Update workflow state
    return {
        **state,
        "messages": agent_state.messages,
        "risk_level": risk_level,
        "crisis_detected": crisis_detected,
        "next_step": "resource_matching" if crisis_detected else "support_resources"
    }


async def resource_matching_node(state: WorkflowState) -> WorkflowState:
    """
    Resource Matching Node - Finds therapist for user.
    """

    logger.info("=" * 70)
    logger.info("🔍 WORKFLOW: Resource Matching Starting")
    logger.info("=" * 70)

    # Create Resource Agent
    resource_agent = ResourceAgent()

    # Convert workflow state to agent state
    agent_state = AgentState(
        messages=state["messages"],
        user_id=state["user_id"],
        privacy_tier=state["privacy_tier"]
    )

    # Add user needs based on crisis assessment
    specialization = None
    if state.get("risk_level") in ["high", "immediate"]:
        specialization = "trauma"  # High-risk cases need trauma specialists

    agent_state = resource_agent.update_agent_data(
        agent_state,
        "user_needs",
        {"specialization": specialization}
    )

    # Run Resource Agent
    agent_state = await resource_agent.process(agent_state)

    # Extract matching results
    matched_therapist = agent_state.agent_data.get("matched_therapist")

    therapist_matched = matched_therapist is not None
    therapist_id = matched_therapist.get("id") if matched_therapist else None
    therapist_name = matched_therapist.get("name") if matched_therapist else None

    logger.info(f"🎯 Resource Matching Complete: Match Found = {therapist_matched}")
    if therapist_name:
        logger.info(f"   Matched with: {therapist_name}")

    # Update workflow state
    return {
        **state,
        "messages": agent_state.messages,
        "therapist_matched": therapist_matched,
        "matched_therapist_id": therapist_id,
        "matched_therapist_name": therapist_name,
        "workflow_complete": not state.get("needs_habit_support", False)
    }


async def support_resources_node(state: WorkflowState) -> WorkflowState:
    """
    Support Resources Node - For low/no risk cases.
    """

    logger.info("=" * 70)
    logger.info("💚 WORKFLOW: Providing Support Resources (No Crisis)")
    logger.info("=" * 70)

    logger.info("✅ Support resources provided")

    return {
        **state,
        "workflow_complete": not state.get("needs_habit_support", False)
    }


async def habit_support_node(state: WorkflowState) -> WorkflowState:
    """
    Habit Support Node - Suggests supportive routines after escalation.
    """

    logger.info("=" * 70)
    logger.info("📈 WORKFLOW: Habit Agent providing follow-up plan")
    logger.info("=" * 70)

    habit_agent = HabitAgent()
    agent_state = AgentState(
        messages=state["messages"],
        user_id=state["user_id"],
        privacy_tier=state["privacy_tier"]
    )

    # Pass contextual hints from coordinator if available
    if state.get("coordinator_plan"):
        agent_state = habit_agent.update_agent_data(
            agent_state,
            "coordinator_plan",
            state["coordinator_plan"]
        )

    agent_state = await habit_agent.process(agent_state)
    habit_plan = agent_state.agent_data.get("habit_plan")

    return {
        **state,
        "messages": agent_state.messages,
        "habit_plan_created": True,
        "needs_habit_support": False,
        "habit_plan": habit_plan,
        "workflow_complete": True
    }


# ================================================================
# ROUTING LOGIC
# ================================================================


def route_after_coordinator(state: WorkflowState) -> Literal["intake", "crisis_assessment"]:
    """
    Coordinator decides whether to start with Intake or jump to Crisis.
    """

    next_step = state.get("next_step") or "intake"

    if next_step == "crisis_assessment":
        logger.info("🔀 ROUTING: Coordinator → Crisis Assessment")
        return "crisis_assessment"

    logger.info("🔀 ROUTING: Coordinator → Intake Conversation")
    return "intake"


def route_after_intake(state: WorkflowState) -> Literal["intake", "crisis_assessment"]:
    """
    Decide whether to continue intake or proceed to crisis assessment.

    IF intake complete:
        → Go to crisis_assessment
    ELSE:
        → Continue intake conversation (loop back)
    """

    if state.get("intake_complete", False):
        logger.info("🔀 ROUTING: Intake complete → Crisis Assessment")
        return "crisis_assessment"
    else:
        logger.info("🔀 ROUTING: Intake ongoing → Continue conversation")
        return "intake"


def route_after_crisis(state: WorkflowState) -> Literal["resource_matching", "support_resources"]:
    """
    Decide what to do after crisis assessment.
    """

    if state.get("crisis_detected", False):
        logger.info("🔀 ROUTING: Crisis detected → Resource Matching")
        return "resource_matching"
    else:
        logger.info("🔀 ROUTING: No crisis → Support Resources")
        return "support_resources"


def route_after_resource(state: WorkflowState) -> Literal["habit_support", "end"]:
    """
    Decide whether to add Habit Agent after resource matching.
    """

    if state.get("needs_habit_support"):
        logger.info("🔀 ROUTING: Queue Habit Agent for follow-up")
        return "habit_support"

    logger.info("🔀 ROUTING: No habit support needed → End workflow")
    return "end"


def route_after_support(state: WorkflowState) -> Literal["habit_support", "end"]:
    """
    Decide whether to offer habits after support resources.
    """

    if state.get("needs_habit_support"):
        logger.info("🔀 ROUTING: Support resources delivered → Habit Agent next")
        return "habit_support"

    logger.info("🔀 ROUTING: Support resources complete → End workflow")
    return "end"


# ================================================================
# WORKFLOW CREATION
# ================================================================

def create_intake_crisis_workflow():
    """
    Create the Intake → Crisis → Resource workflow.

    GRAPH STRUCTURE:

    START
      ↓
    [Coordinator] ──► (Intake or direct Crisis)
          ↓
    [Intake] ←─┐ (loops until complete)
          ↓    │
    {Complete?}┘
          ↓
    [Crisis Assessment]
          ↓
    {Is crisis?}
      ↓          ↓
    YES         NO
      ↓          ↓
    [Resource   [Support
     Matching]   Resources]
          ↓          ↓
    {Habits?}    {Habits?}
      ↓  ↓         ↓   ↓
    YES  NO      YES  NO
      ↓   ↓        ↓   ↓
    [Habit] END  [Habit] END
    """

    logger.info("🏗️  Building Intake → Crisis → Resource workflow...")

    # Create the graph with our state schema
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("coordinator", coordinator_node)
    workflow.add_node("intake", intake_node)
    workflow.add_node("crisis_assessment", crisis_assessment_node)
    workflow.add_node("resource_matching", resource_matching_node)
    workflow.add_node("support_resources", support_resources_node)
    workflow.add_node("habit_support", habit_support_node)

    # Add edges

    # START → coordinator
    workflow.add_edge(START, "coordinator")

    # coordinator → intake or crisis
    workflow.add_conditional_edges(
        "coordinator",
        route_after_coordinator,
        {
            "intake": "intake",
            "crisis_assessment": "crisis_assessment",
        }
    )

    # intake → ??? (conditional: continue intake OR proceed to crisis)
    workflow.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "intake": "intake",  # Loop back for more conversation
            "crisis_assessment": "crisis_assessment"
        }
    )

    # crisis_assessment → ??? (conditional routing)
    workflow.add_conditional_edges(
        "crisis_assessment",
        route_after_crisis,
        {
            "resource_matching": "resource_matching",
            "support_resources": "support_resources"
        }
    )

    # resource_matching → habit support or END
    workflow.add_conditional_edges(
        "resource_matching",
        route_after_resource,
        {
            "habit_support": "habit_support",
            "end": END
        }
    )

    # support_resources → habit support or END
    workflow.add_conditional_edges(
        "support_resources",
        route_after_support,
        {
            "habit_support": "habit_support",
            "end": END
        }
    )

    # Habit agent always ends the workflow
    workflow.add_edge("habit_support", END)

    # Compile the workflow
    compiled_workflow = workflow.compile()

    logger.info("✅ Workflow compiled successfully")
    logger.info("   Nodes: coordinator, intake, crisis_assessment, resource_matching, support_resources, habit_support")
    logger.info("   Routing: Coordinator-driven multi-agent flow")

    return compiled_workflow


# ================================================================
# CONVENIENCE FUNCTION
# ================================================================

async def run_intake_workflow(
    user_message: str,
    user_id: str = "demo_user",
    privacy_tier: str = "full_support"
):
    """
    Run the workflow with a user message.

    This handles multi-turn conversations automatically!
    """

    logger.info("=" * 70)
    logger.info("🚀 STARTING INTAKE WORKFLOW")
    logger.info("=" * 70)
    logger.info(f"User Message: {user_message}")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Privacy Tier: {privacy_tier}")
    logger.info("=" * 70)

    # Create workflow
    workflow = create_intake_crisis_workflow()

    # Initialize state
    initial_state: WorkflowState = {
        "messages": [HumanMessage(content=user_message)],
        "user_id": user_id,
        "privacy_tier": privacy_tier,
        "coordinator_plan": None,
        "needs_habit_support": False,
        "habit_plan_created": False,
        "habit_plan": None,
        "intake_complete": False,
        "intake_stage": None,
        "risk_level": None,
        "crisis_detected": False,
        "therapist_matched": False,
        "matched_therapist_id": None,
        "matched_therapist_name": None,
        "next_step": None,
        "workflow_complete": False
    }

    # Run workflow
    final_state = await workflow.ainvoke(initial_state)

    logger.info("=" * 70)
    logger.info("✅ WORKFLOW COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Intake Complete: {final_state.get('intake_complete')}")
    logger.info(f"Risk Level: {final_state.get('risk_level')}")
    logger.info(f"Crisis Detected: {final_state.get('crisis_detected')}")
    logger.info(f"Therapist Matched: {final_state.get('therapist_matched')}")
    if final_state.get('matched_therapist_name'):
        logger.info(f"Matched With: {final_state.get('matched_therapist_name')}")
    logger.info("=" * 70)

    return final_state


# ================================================================
# EXAMPLE USAGE
# ================================================================

if __name__ == "__main__":
    import asyncio

    async def test_workflow():
        """Test the intake workflow."""

        print("\n" + "=" * 70)
        print("🧪 Testing Intake Workflow")
        print("=" * 70)
        print()

        # Test with initial greeting
        result = await run_intake_workflow(
            user_message="Hi, I need help",
            user_id="test_user_1"
        )

        print("\n📊 Result:")
        print(f"   Messages exchanged: {len(result['messages'])}")
        print(f"   Intake complete: {result['intake_complete']}")
        print(f"   Last response: {result['messages'][-1].content[:200]}...")

    asyncio.run(test_workflow())
