"""
Crisis Assessment Agent - ReAct Pattern Implementation
=======================================================

This agent demonstrates TRUE agentic AI using the ReAct pattern:
Reasoning + Acting in a loop until task is complete.

ReAct Pattern:
1. THOUGHT: "What should I do next?"
2. ACTION: Execute a tool/function
3. OBSERVATION: See the result
4. Repeat until done

This is what makes it AGENTIC vs a simple chatbot!
"""

from typing import Dict, Any, List, Literal, Optional
from datetime import datetime
from enum import Enum

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent, AgentState
from loguru import logger


# ================================================================
# CRISIS RISK LEVELS - Clear categories for decision-making
# ================================================================

class RiskLevel(str, Enum):
    """Risk assessment categories."""
    NONE = "none"           # No risk indicators
    LOW = "low"             # Mild distress, manageable
    MODERATE = "moderate"   # Concerning patterns
    HIGH = "high"           # Serious warning signs
    IMMEDIATE = "immediate" # Crisis requiring immediate intervention


# ================================================================
# CRISIS INDICATORS - What patterns to look for
# ================================================================

# These are the warning signs the agent will detect
CRISIS_KEYWORDS = {
    "immediate": [
        "suicide", "kill myself", "end it all", "not worth living",
        "better off dead", "plan to die", "overdose", "want to die"
    ],
    "high": [
        "hopeless", "can't go on", "no way out", "unbearable pain",
        "nothing matters", "give up", "pointless", "burden"
    ],
    "moderate": [
        "depressed", "anxious", "can't sleep", "overwhelming",
        "struggling", "falling apart", "losing control"
    ],
    "low": [
        "stressed", "worried", "down", "upset", "difficult time",
        "not feeling great", "having a rough day"
    ]
}


# ================================================================
# CRISIS AGENT TOOLS - Functions the agent can call
# ================================================================

# LEARNING NOTE: @tool decorator makes this callable by the LLM
# The LLM can decide "I should use assess_message_risk" and call it
# This is TOOL CALLING - a key feature of agentic AI

@tool
def assess_message_risk(message: str) -> Dict[str, Any]:
    """Analyze a message for crisis indicators and return risk assessment."""

    # Convert to lowercase for matching
    message_lower = message.lower()

    # Check each risk level (highest to lowest priority)
    found_keywords = []
    detected_level = RiskLevel.NONE

    # Check immediate risk first (most critical)
    for keyword in CRISIS_KEYWORDS["immediate"]:
        if keyword in message_lower:
            found_keywords.append(keyword)
            detected_level = RiskLevel.IMMEDIATE

    # If no immediate risk, check high risk
    if detected_level == RiskLevel.NONE:
        for keyword in CRISIS_KEYWORDS["high"]:
            if keyword in message_lower:
                found_keywords.append(keyword)
                detected_level = RiskLevel.HIGH

    # Then moderate
    if detected_level == RiskLevel.NONE:
        for keyword in CRISIS_KEYWORDS["moderate"]:
            if keyword in message_lower:
                found_keywords.append(keyword)
                detected_level = RiskLevel.MODERATE

    # Finally low
    if detected_level == RiskLevel.NONE:
        for keyword in CRISIS_KEYWORDS["low"]:
            if keyword in message_lower:
                found_keywords.append(keyword)
                detected_level = RiskLevel.LOW

    return {
        "risk_level": detected_level.value,
        "keywords_found": found_keywords,
        "message_length": len(message),
        "timestamp": datetime.now().isoformat()
    }


@tool
def get_crisis_resources(location: Optional[str] = None) -> Dict[str, Any]:
    """Get crisis hotline and emergency resources."""

    # In production, this would use Tavily to search for local resources
    # For now, return essential crisis contacts

    resources = {
        "national_crisis_line": {
            "name": "988 Suicide & Crisis Lifeline",
            "phone": "988",
            "text": "Text 988",
            "chat": "https://988lifeline.org/chat",
            "available": "24/7"
        },
        "crisis_text_line": {
            "name": "Crisis Text Line",
            "text": "Text HOME to 741741",
            "available": "24/7"
        },
        "emergency": {
            "name": "Emergency Services",
            "phone": "911",
            "when": "Immediate danger"
        }
    }

    return {
        "resources": resources,
        "location": location or "United States (default)"
    }


@tool
def should_escalate(risk_level: str, conversation_context: str) -> Dict[str, bool]:
    """Determine if situation needs escalation to resource agent or emergency services."""

    # Simple escalation logic
    needs_emergency = risk_level == RiskLevel.IMMEDIATE.value
    needs_resource_agent = risk_level in [
        RiskLevel.HIGH.value,
        RiskLevel.MODERATE.value
    ]

    return {
        "needs_emergency_services": needs_emergency,
        "needs_resource_agent": needs_resource_agent,
        "needs_monitoring": risk_level != RiskLevel.NONE.value,
        "recommendation": _get_escalation_recommendation(risk_level)
    }


def _get_escalation_recommendation(risk_level: str) -> str:
    """Get recommendation text based on risk level."""

    recommendations = {
        RiskLevel.IMMEDIATE.value: "IMMEDIATE ACTION: Provide crisis resources and consider emergency services",
        RiskLevel.HIGH.value: "HIGH PRIORITY: Connect with Resource Agent for therapist matching",
        RiskLevel.MODERATE.value: "MODERATE: Suggest therapist check-in and monitor closely",
        RiskLevel.LOW.value: "LOW: Provide support and coping strategies",
        RiskLevel.NONE.value: "NONE: Continue conversation normally"
    }

    return recommendations.get(risk_level, "Unknown risk level")


# ================================================================
# CRISIS AGENT - ReAct Pattern Implementation
# ================================================================

class CrisisAgent(BaseAgent):
    """
    Crisis Assessment Agent using ReAct pattern.

    Autonomously assesses crisis risk through:
    1. Analyzing messages for warning signs
    2. Determining appropriate response level
    3. Escalating when necessary
    4. Providing crisis resources
    """

    def __init__(self):
        # Initialize base agent with crisis-specific settings
        super().__init__(
            agent_name="Crisis Agent",
            temperature=0.3,  # Lower temperature = more consistent, less creative
                             # Crisis assessment needs consistency, not creativity!
            max_tokens=512,   # Crisis responses should be concise
        )

        # Bind tools to the LLM so it can call them
        # This is the key to ReAct - giving the LLM functions it can execute
        self.tools = [
            assess_message_risk,
            get_crisis_resources,
            should_escalate
        ]

        # Create LLM with tools bound
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        logger.info("🚨 Crisis Agent initialized with ReAct capabilities")


    def get_system_prompt(self) -> str:
        """System prompt that defines the agent's role and behavior."""

        # LEARNING NOTE: This prompt shapes how the agent thinks
        # Notice we tell it WHEN to use tools (ReAct pattern)

        return """You are a Crisis Assessment Agent for a mental health support platform.

Your role:
1. Analyze user messages for crisis indicators
2. Use tools to assess risk level systematically
3. Escalate appropriately based on severity
4. Provide crisis resources when needed
5. Be empathetic but action-oriented

Tools available:
- assess_message_risk: Analyze messages for warning signs
- get_crisis_resources: Retrieve crisis hotlines and resources
- should_escalate: Determine if escalation is needed

ReAct Pattern (use this approach):
1. THOUGHT: Consider what action to take
2. ACTION: Use a tool to gather information
3. OBSERVATION: Review the tool's output
4. DECISION: Based on observations, respond or use another tool

IMPORTANT:
- Always start by assessing message risk
- If IMMEDIATE or HIGH risk, provide crisis resources
- Be warm and non-judgmental
- Keep responses concise and actionable
- Never diagnose or prescribe
"""


    async def process(self, state: AgentState) -> AgentState:
        """Main processing logic using ReAct pattern."""

        # STEP 1: Extract the latest user message
        # ========================================
        if not state.messages:
            logger.warning("No messages to process")
            return state

        # Get the last user message
        last_message = state.messages[-1]
        user_message = last_message.content if hasattr(last_message, 'content') else str(last_message)

        logger.info(f"🔍 Analyzing message for crisis indicators...")


        # STEP 2: Build conversation for LLM
        # ===================================
        # System prompt + conversation history
        messages = [
            SystemMessage(content=self.get_system_prompt())
        ]

        # Add recent conversation (last 5 messages for context)
        recent_messages = self.get_conversation_history(state, max_messages=5)
        messages.extend(recent_messages)


        # STEP 3: ReAct Loop - Let LLM decide what tools to use
        # ======================================================
        # The LLM will:
        # 1. Think about what to do
        # 2. Call tools (assess_message_risk, etc.)
        # 3. See results
        # 4. Decide next action
        # This continues until it has enough info to respond

        max_iterations = 5  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Call LLM with tools
            logger.debug(f"🧠 ReAct iteration {iteration}/{max_iterations}")
            response = await self.llm_with_tools.ainvoke(messages)

            # Add LLM response to messages
            messages.append(response)

            # Check if LLM wants to use tools
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # LEARNING NOTE: This is the "ACTION" part of ReAct
                # The LLM decided to call a tool!

                logger.info(f"🛠️  Agent calling {len(response.tool_calls)} tool(s)")

                # Execute each tool call
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']

                    logger.debug(f"   └─ {tool_name}({tool_args})")

                    # Execute the tool
                    tool_result = await self._execute_tool(tool_name, tool_args)

                    # LEARNING NOTE: This is the "OBSERVATION" part of ReAct
                    # The agent sees what the tool returned

                    # Capture structured insights for downstream agents/workflow
                    if isinstance(tool_result, dict):
                        if tool_name == "assess_message_risk":
                            state = self.update_agent_data(state, "risk_assessment", tool_result)
                            state = self.update_agent_data(state, "risk_level", tool_result.get("risk_level"))
                        elif tool_name == "should_escalate":
                            state = self.update_agent_data(state, "escalation_recommendation", tool_result)
                            state = self.update_agent_data(
                                state,
                                "needs_resource_agent",
                                tool_result.get("needs_resource_agent", False)
                            )
                            state = self.update_agent_data(
                                state,
                                "needs_emergency_services",
                                tool_result.get("needs_emergency_services", False)
                            )
                        elif tool_name == "get_crisis_resources":
                            state = self.update_agent_data(state, "crisis_resources", tool_result.get("resources"))

                    # Add tool result to conversation
                    # The LLM will see this in the next iteration
                    messages.append(
                        HumanMessage(
                            content=f"Tool '{tool_name}' returned: {tool_result}"
                        )
                    )

                    # Log the decision for demo
                    self.log_decision(
                        f"tool_execution_{tool_name}",
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "result": tool_result
                        }
                    )

                # Continue loop - LLM will think about tool results
                continue

            else:
                # No more tools to call - LLM has final response
                # This is when ReAct loop completes

                logger.info("✅ Crisis assessment complete")

                # Extract the response content
                final_response = response.content

                # Add to state
                state = self.add_message(state, "assistant", final_response)

                # Log final decision
                self.log_decision(
                    "crisis_assessment_complete",
                    {
                        "iterations": iteration,
                        "response_length": len(final_response)
                    }
                )

                break

        return state


    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """Execute a tool by name with given arguments."""

        # Map tool names to functions
        tool_map = {
            "assess_message_risk": assess_message_risk,
            "get_crisis_resources": get_crisis_resources,
            "should_escalate": should_escalate
        }

        if tool_name not in tool_map:
            logger.error(f"Unknown tool: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            # Execute the tool function
            tool_func = tool_map[tool_name]
            result = tool_func.invoke(tool_args)
            return result

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"error": str(e)}


# ================================================================
# USAGE EXAMPLE (for testing)
# ================================================================

"""
Example: Using Crisis Agent with ReAct

The agent will autonomously:
1. Assess the message for crisis keywords
2. Determine risk level
3. Decide if escalation is needed
4. Provide appropriate resources
5. Respond empathetically

All of this happens WITHOUT us telling it the exact steps!
The ReAct pattern lets the LLM decide what tools to use and when.
"""
