"""
Habit Agent - Gentle Follow-Through Coaching
============================================

The Habit Agent provides lightweight accountability once a user has
been matched with support. It recommends small, achievable routines
based on the conversation context and keeps the multi-agent workflow
going after crisis/resource handling.
"""

from typing import List, Dict

from loguru import logger

from .base_agent import BaseAgent, AgentState


class HabitAgent(BaseAgent):
    """
    Suggests supportive micro-habits tailored to the user's needs.

    For hackathon purposes we generate structured, empathetic guidance
    deterministically so the demo is reliable even without additional
    LLM calls.
    """

    KEYWORD_LIBRARY: Dict[str, Dict[str, str]] = {
        "burnout": {
            "title": "End-of-day decompress",
            "description": "Take a short walk without screens right after work to reset before studying.",
        },
        "sleep": {
            "title": "Evening wind-down journal",
            "description": "Spend 5 minutes jotting what went well and what can wait until tomorrow.",
        },
        "anxiety": {
            "title": "2-minute breathing reset",
            "description": "Three cycles of four-count breathing whenever you notice tension building.",
        },
        "purpose": {
            "title": "Weekly reflection checkpoint",
            "description": "Every Sunday, write one sentence about progress toward what matters most to you.",
        },
        "default": {
            "title": "Micro-win tracker",
            "description": "Capture one small win each day to review with your therapist.",
        },
    }

    def __init__(self):
        super().__init__(
            agent_name="Habit Agent",
            temperature=0.4,
            max_tokens=256,
        )
        logger.info("📈 Habit Agent initialized - ready to suggest routines")

    def get_system_prompt(self) -> str:
        """
        We do not rely on the LLM response for the hackathon demo, but the
        prompt remains for future expansion.
        """

        return (
            "You are the Habit Agent creating short supportive routines. "
            "Keep recommendations compassionate, doable, and specific."
        )

    async def process(self, state: AgentState) -> AgentState:
        """
        Build a simple habit plan from conversation cues.
        """

        if not state.messages:
            return state

        user_context = self._gather_user_context(state)
        habit_plan = self._generate_plan(user_context)

        response_lines = ["Here’s a gentle habit plan you can start right away:"]
        for idx, item in enumerate(habit_plan, start=1):
            response_lines.append(f"{idx}. {item['title']}: {item['description']}")
        response_lines.append("Feel free to share these with your therapist during your first session.")

        response_text = "\n".join(response_lines)
        state = self.add_message(state, "assistant", response_text)

        self.log_decision(
            "habit_plan_created",
            {"habits": habit_plan, "context_excerpt": user_context[:160]},
        )

        state = self.update_agent_data(state, "habit_plan", habit_plan)
        return state

    def _gather_user_context(self, state: AgentState) -> str:
        """
        Combine recent human messages for lightweight context.
        """

        user_messages = [
            getattr(message, "content", "")
            for message in state.messages
            if getattr(message, "type", "") == "human"
        ]
        return " ".join(user_messages).lower()

    def _generate_plan(self, context: str) -> List[Dict[str, str]]:
        """
        Simple keyword-based habit suggestions.
        """

        matches: List[Dict[str, str]] = []
        for keyword, habit in self.KEYWORD_LIBRARY.items():
            if keyword == "default":
                continue
            if keyword in context:
                matches.append(habit)

        if not matches:
            matches.append(self.KEYWORD_LIBRARY["purpose"])
            matches.append(self.KEYWORD_LIBRARY["default"])
        else:
            matches.append(self.KEYWORD_LIBRARY["default"])

        # Guarantee at most three habits to keep output digestible.
        return matches[:3]
