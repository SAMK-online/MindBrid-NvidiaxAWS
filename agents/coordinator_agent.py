"""
Coordinator Agent - High-Level Orchestration Brain
==================================================

This agent is the "traffic director" for MindBridge. It inspects the
incoming user context, decides which specialists should engage, and
shares a lightweight plan for the rest of the workflow. This makes the
multi-agent reasoning explicit for demos and logging.
"""

from typing import List

from loguru import logger

from .base_agent import BaseAgent, AgentState


class CoordinatorAgent(BaseAgent):
    """
    Coordinator Agent orchestrates MindBridge specialists.

    Responsibilities:
    - Inspect the latest user message
    - Decide whether to start with Intake or jump to Crisis Agent
    - Flag downstream needs (e.g., habit coaching)
    - Log a high-level plan of action for visualization
    """

    CRISIS_KEYWORDS = {
        "immediate": ["suicide", "kill myself", "end it all", "911"],
        "high": ["hopeless", "no way out", "can't go on", "burden"],
    }

    HABIT_KEYWORDS = [
        "habit",
        "routine",
        "track",
        "streak",
        "plan",
        "practice",
        "consistency",
    ]

    def __init__(self):
        super().__init__(
            agent_name="Coordinator Agent",
            temperature=0.1,
            max_tokens=240,
            model_name="nvidia/llama-3.3-nemotron-super-49b-v1.5"
        )
        logger.info("🎯 Coordinator Agent ready - orchestrating specialists")

    def get_system_prompt(self) -> str:
        """
        Short system prompt so the coordinator keeps outputs concise.
        """

        return (
            "You are the Coordinator Agent for MindBridge. "
            "Inspect the latest user message, decide which specialist "
            "agent should handle the situation (Intake vs Crisis), note whether "
            "habit coaching will be helpful, and produce a short bullet list plan. "
            "Respond in plain text (no JSON)."
        )

    async def process(self, state: AgentState) -> AgentState:
        """
        Examine the user's latest message and set routing metadata.
        """

        if not state.messages:
            return state

        latest_message = state.messages[-1].content.lower()
        plan_steps: List[str] = []

        # Default route is warm intake unless clear crisis language is present.
        initial_route = "intake"
        crisis_level = self._detect_crisis_level(latest_message)

        if crisis_level in {"high", "immediate"}:
            initial_route = "crisis_assessment"
            plan_steps.append("🚨 Route directly to Crisis Agent for immediate triage.")
        else:
            plan_steps.append("🤝 Begin with Intake Agent to build context and trust.")
            plan_steps.append("🧠 Forward context to Crisis Agent for risk scoring.")

        needs_habit_support = any(keyword in latest_message for keyword in self.HABIT_KEYWORDS)
        if needs_habit_support:
            plan_steps.append("📈 Queue Habit Agent to suggest supportive routines.")

        # Record routing in agent data for the workflow to consume.
        state = self.update_agent_data(state, "initial_route", initial_route)
        state = self.update_agent_data(state, "needs_habit_support", needs_habit_support)
        state = self.update_agent_data(state, "coordinator_plan", plan_steps)

        # Share a short human-readable plan with the message log.
        summary_lines = ["Coordinator Plan:"]
        summary_lines.extend(plan_steps or ["→ Proceed with default workflow."])
        summary_lines.append(f"Next Specialist: {initial_route.replace('_', ' ').title()}")

        coordinator_response = "\n".join(summary_lines)
        state = self.add_message(state, "assistant", coordinator_response)

        self.log_decision(
            "coordination_plan",
            {
                "initial_route": initial_route,
                "needs_habit_support": needs_habit_support,
                "plan_steps": plan_steps,
                "crisis_level": crisis_level,
            },
        )

        return state

    def _detect_crisis_level(self, message: str) -> str:
        """
        Quickly check for crisis keywords. The Crisis Agent will perform
        the full ReAct analysis later; this just steers the workflow.
        """

        for keyword in self.CRISIS_KEYWORDS["immediate"]:
            if keyword in message:
                return "immediate"
        for keyword in self.CRISIS_KEYWORDS["high"]:
            if keyword in message:
                return "high"

        return "none"
