"""
Crisis to Resource Workflow - Multi-Agent Orchestration
========================================================

This LangGraph workflow demonstrates TRUE multi-agent coordination:

FLOW:
1. User sends message
2. Crisis Agent assesses risk
3. IF high/moderate risk → Resource Agent finds therapist
4. IF low/none risk → Provide support resources
5. Return final response

This shows:
- Agent handoffs (Crisis → Resource)
- Conditional routing (based on risk level)
- State management across agents
- Autonomous decision-making

KEY CONCEPT: Agents work together, each doing their specialized task!
"""

from typing import TypedDict, Literal, Annotated, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from loguru import logger

from agents.crisis_agent import CrisisAgent
from agents.resource_agent import ResourceAgent
from agents.base_agent import AgentState


# ================================================================
# WORKFLOW STATE
# ================================================================
# This is the shared state that flows between all agents
# Think of it as a "clipboard" that agents pass around

class WorkflowState(TypedDict):
    """
    State that flows through the entire workflow.

    LangGraph automatically manages this state:
    - Each agent can read from it
    - Each agent can update it
    - Updates are merged automatically
    """

    # Conversation messages (automatically merged with add_messages)
    messages: Annotated[list[BaseMessage], add_messages]

    # User information
    user_id: str
    privacy_tier: str

    # Crisis assessment results
    risk_level: Optional[str]  # "none", "low", "moderate", "high", "immediate"
    crisis_detected: bool

    # Resource matching results
    therapist_matched: bool
    matched_therapist_id: Optional[str]
    matched_therapist_name: Optional[str]

    # Escalation guidance
    needs_resource_agent: bool
    needs_emergency_services: bool
    escalation_recommendation: Optional[dict]

    # Workflow control
    next_step: Optional[str]  # Which agent to call next
    workflow_complete: bool


# ================================================================
# AGENT NODE FUNCTIONS
# ================================================================
# These wrap our agents for use in LangGraph
# Each function is a "node" in the graph

async def crisis_assessment_node(state: WorkflowState) -> WorkflowState:
    """
    Crisis Assessment Node - First step in workflow.

    This node:
    1. Takes the workflow state
    2. Runs Crisis Agent
    3. Updates state with risk assessment
    4. Returns updated state

    LangGraph then decides where to route next based on the state!
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

    # Prefer structured insight from Crisis Agent (populated during tool calls)
    risk_level = agent_state.agent_data.get("risk_level")
    escalation = agent_state.agent_data.get("escalation_recommendation", {})
    needs_resource = agent_state.agent_data.get("needs_resource_agent", False)
    needs_emergency = agent_state.agent_data.get("needs_emergency_services", False)

    if not risk_level:
        response_text = agent_state.messages[-1].content.lower() if agent_state.messages else ""
        if any(word in response_text for word in ["immediate", "emergency", "911"]):
            risk_level = "immediate"
        elif any(word in response_text for word in ["high priority", "therapist", "connect you"]):
            risk_level = "high"
        elif any(word in response_text for word in ["moderate", "check-in", "follow up"]):
            risk_level = "moderate"
        elif any(word in response_text for word in ["low", "stressed", "support"]):
            risk_level = "low"
        else:
            risk_level = "none"

    crisis_detected = risk_level in ["moderate", "high", "immediate"] or needs_resource or needs_emergency

    logger.info(f"🎯 Crisis Assessment Complete: Risk Level = {risk_level}")

    # Update workflow state
    return {
        **state,
        "messages": agent_state.messages,
        "risk_level": risk_level,
        "crisis_detected": crisis_detected,
        "needs_resource_agent": needs_resource,
        "needs_emergency_services": needs_emergency,
        "escalation_recommendation": escalation,
        "next_step": "resource_matching" if crisis_detected else "end"
    }


async def resource_matching_node(state: WorkflowState) -> WorkflowState:
    """
    Resource Matching Node - Second step (if crisis detected).

    This node:
    1. Takes state from Crisis Agent
    2. Runs Resource Agent to find therapist
    3. Updates state with match results
    4. Returns updated state
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
    # In production, this would be more sophisticated
    specialization = None
    if state.get("risk_level") in ["high", "immediate"]:
        specialization = "trauma"  # High-risk cases need trauma specialists

    agent_state = resource_agent.update_agent_data(
        agent_state,
        "user_needs",
        {"specialization": specialization}
    )

    # Run Resource Agent (this does autonomous search if needed)
    agent_state = await resource_agent.process(agent_state)

    # Extract matching results
    matched_therapist = agent_state.agent_data.get("matched_therapist")

    therapist_matched = matched_therapist is not None
    therapist_id = matched_therapist.get("id") if matched_therapist else None
    therapist_name = matched_therapist.get("name") if matched_therapist else None

    logger.info(
        f"🎯 Resource Matching Complete: Match Found = {therapist_matched}"
    )
    if therapist_name:
        logger.info(f"   Matched with: {therapist_name}")

    # Update workflow state
    return {
        **state,
        "messages": agent_state.messages,
        "therapist_matched": therapist_matched,
        "matched_therapist_id": therapist_id,
        "matched_therapist_name": therapist_name,
        "needs_resource_agent": False,
        "workflow_complete": True
    }


async def support_resources_node(state: WorkflowState) -> WorkflowState:
    """
    Support Resources Node - For low/no risk cases.

    This provides general support resources without therapist matching.
    For demo purposes, we just log this step.
    """

    logger.info("=" * 70)
    logger.info("💚 WORKFLOW: Providing Support Resources (No Crisis)")
    logger.info("=" * 70)

    # In production, this would provide:
    # - Self-help resources
    # - Coping strategies
    # - Community support links
    # - Wellness tips

    logger.info("✅ Support resources provided")

    return {
        **state,
        "needs_resource_agent": False,
        "workflow_complete": True
    }


# ================================================================
# ROUTING LOGIC
# ================================================================
# These functions determine WHERE to go next in the workflow

def route_after_crisis(state: WorkflowState) -> Literal["resource_matching", "support_resources"]:
    """
    Decide what to do after crisis assessment.

    IF crisis detected (moderate/high/immediate):
        → Go to resource_matching (find therapist)
    ELSE (low/none):
        → Go to support_resources (self-help)

    This is CONDITIONAL ROUTING - the graph adapts based on the situation!
    """

    if state.get("crisis_detected", False):
        logger.info("🔀 ROUTING: Crisis detected → Resource Matching")
        return "resource_matching"
    else:
        logger.info("🔀 ROUTING: No crisis → Support Resources")
        return "support_resources"


# ================================================================
# WORKFLOW CREATION
# ================================================================

def create_crisis_resource_workflow():
    """
    Create the Crisis → Resource coordination workflow.

    This builds a LangGraph that orchestrates multiple agents:

    GRAPH STRUCTURE:

    START
      ↓
    [Crisis Assessment]
      ↓
    {Is crisis?}
      ↓           ↓
    YES          NO
      ↓           ↓
    [Resource   [Support
     Matching]   Resources]
      ↓           ↓
    END         END

    Returns:
        Compiled LangGraph workflow ready to execute
    """

    logger.info("🏗️  Building Crisis → Resource workflow...")

    # Create the graph with our state schema
    workflow = StateGraph(WorkflowState)

    # Add nodes (each agent is a node)
    workflow.add_node("crisis_assessment", crisis_assessment_node)
    workflow.add_node("resource_matching", resource_matching_node)
    workflow.add_node("support_resources", support_resources_node)

    # Add edges (define the flow)

    # START → crisis_assessment (always start here)
    workflow.add_edge(START, "crisis_assessment")

    # crisis_assessment → ??? (conditional routing!)
    workflow.add_conditional_edges(
        "crisis_assessment",
        route_after_crisis,
        {
            "resource_matching": "resource_matching",
            "support_resources": "support_resources"
        }
    )

    # Both paths → END
    workflow.add_edge("resource_matching", END)
    workflow.add_edge("support_resources", END)

    # Compile the workflow
    compiled_workflow = workflow.compile()

    logger.info("✅ Workflow compiled successfully")
    logger.info("   Nodes: crisis_assessment, resource_matching, support_resources")
    logger.info("   Routing: Conditional based on crisis level")

    return compiled_workflow


# ================================================================
# CONVENIENCE FUNCTION
# ================================================================

async def run_crisis_resource_workflow(
    user_message: str,
    user_id: str = "demo_user",
    privacy_tier: str = "full_support"
):
    """
    Convenience function to run the workflow with a user message.

    This handles all the state setup and returns the final result.

    Args:
        user_message: What the user said
        user_id: User identifier
        privacy_tier: Privacy level

    Returns:
        Final workflow state with all agent results
    """

    from langchain_core.messages import HumanMessage

    logger.info("=" * 70)
    logger.info("🚀 STARTING MULTI-AGENT WORKFLOW")
    logger.info("=" * 70)
    logger.info(f"User Message: {user_message}")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Privacy Tier: {privacy_tier}")
    logger.info("=" * 70)

    # Create workflow
    workflow = create_crisis_resource_workflow()

    # Initialize state
    initial_state: WorkflowState = {
        "messages": [HumanMessage(content=user_message)],
        "user_id": user_id,
        "privacy_tier": privacy_tier,
        "risk_level": None,
        "crisis_detected": False,
        "needs_resource_agent": False,
        "needs_emergency_services": False,
        "escalation_recommendation": None,
        "therapist_matched": False,
        "matched_therapist_id": None,
        "matched_therapist_name": None,
        "next_step": None,
        "workflow_complete": False
    }

    # Run workflow (LangGraph handles the orchestration!)
    final_state = await workflow.ainvoke(initial_state)

    logger.info("=" * 70)
    logger.info("✅ WORKFLOW COMPLETE")
    logger.info("=" * 70)
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
        """Test the workflow with different scenarios."""

        print("\n" + "=" * 70)
        print("🧪 Testing Multi-Agent Workflow")
        print("=" * 70)

        # Test 1: High-risk message (should trigger full flow)
        print("\n📋 TEST 1: High-Risk Message")
        print("-" * 70)

        result = await run_crisis_resource_workflow(
            user_message="I feel completely hopeless. I don't think I can go on anymore.",
            user_id="test_user_1"
        )

        print("\n📊 Result:")
        print(f"   Messages exchanged: {len(result['messages'])}")
        print(f"   Risk level: {result['risk_level']}")
        print(f"   Therapist matched: {result['therapist_matched']}")

        await asyncio.sleep(2)

        # Test 2: Low-risk message (should skip resource matching)
        print("\n" + "=" * 70)
        print("📋 TEST 2: Low-Risk Message")
        print("-" * 70)

        result = await run_crisis_resource_workflow(
            user_message="I'm feeling a bit stressed about work today.",
            user_id="test_user_2"
        )

        print("\n📊 Result:")
        print(f"   Messages exchanged: {len(result['messages'])}")
        print(f"   Risk level: {result['risk_level']}")
        print(f"   Therapist matched: {result['therapist_matched']}")

        print("\n" + "=" * 70)
        print("✅ Workflow Tests Complete!")
        print("=" * 70)

    asyncio.run(test_workflow())
