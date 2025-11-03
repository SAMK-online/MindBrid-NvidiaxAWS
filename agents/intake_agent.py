"""
Intake Agent - Friendly Conversational Onboarding
==================================================

This agent provides a warm, gradual introduction to the platform.

FLOW:
1. Greet warmly
2. Ask how they're doing
3. Ask what brings them here
4. Ask about what's troubling them
5. Gather details in a calming, supportive way
6. Only THEN assess and route appropriately

KEY PRINCIPLES:
- Warm and friendly tone
- No rushing
- Active listening
- Validation of feelings
- Gradual information gathering
- Human-like conversation flow
"""

from typing import Optional, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from loguru import logger

from .base_agent import BaseAgent, AgentState


class IntakeAgent(BaseAgent):
    """
    Intake Agent for warm, conversational onboarding.

    This agent creates a safe, calming space for users to share
    at their own pace. It follows a gentle conversation flow:
    - Greeting
    - Check-in on current state
    - Understand what brought them here
    - Explore what's troubling them
    - Gather context naturally
    - Build trust before any assessment
    """

    # Conversation stages (tracked in agent_data)
    STAGE_GREETING = "greeting"
    STAGE_CHECK_IN = "check_in"
    STAGE_WHAT_BRINGS_YOU = "what_brings_you"
    STAGE_EXPLORE_TROUBLE = "explore_trouble"
    STAGE_GATHER_CONTEXT = "gather_context"
    STAGE_READY_FOR_ASSESSMENT = "ready_for_assessment"

    EMOTION_KEYWORDS = {
        "stressed", "anxious", "anxiety", "overwhelmed", "lost", "hopeless",
        "sad", "down", "tired", "burned", "burnt", "exhausted", "mess"
    }
    SUPPORT_KEYWORDS = {
        "help", "support", "talk", "therapy", "therapist", "someone", "guidance",
        "volunteer", "counselor", "listen"
    }
    CRISIS_KEYWORDS = {
        "kill myself", "end it all", "suicide", "hurt myself", "hang myself",
        "take my life", "die", "overdose", "can't go on", "no reason to live",
        "want to end everything"
    }

    def __init__(self):
        super().__init__(
            agent_name="Intake Agent",
            temperature=0.85,  # Balanced - warm but consistent
            max_tokens=250     # Room for 2 natural sentences
        )

        logger.info("🤝 Intake Agent initialized - Ready to provide warm welcome")

    def get_system_prompt(self) -> str:
        """System prompt for friendly, calming conversation."""
        return """You are Nima, a warm mental health support AI from MindBridge.

Your job: Have a natural, empathetic conversation to understand what's troubling the user.

Rules:
- Keep responses to 2 sentences maximum
- Be warm, caring, and human
- Ask thoughtful questions to understand their situation
- NEVER repeat yourself - each response must be different

After 3-4 exchanges, offer to connect them with a volunteer therapist."""

    async def process(self, state: AgentState) -> AgentState:
        """
        Process conversation through warm intake stages.

        This tracks conversation stage and guides the user through
        a natural, calming intake process.
        """

        logger.info("🤝 Starting intake conversation...")

        # Determine current conversation stage
        current_stage = state.agent_data.get("intake_stage", self.STAGE_GREETING)

        logger.debug(f"📍 Current intake stage: {current_stage}")

        # Detect immediate crisis cues before proceeding with standard flow
        last_user_message = self._get_last_user_message(state)
        if last_user_message and self._contains_immediate_risk(last_user_message.content):
            logger.warning("🚨 Emergency language detected during intake")
            emergency_reply = (
                "Thank you for trusting me with that. Your safety matters more than anything right now. "
                "If you can, please call or text 988 (Suicide & Crisis Lifeline) or dial 911 immediately. "
                "I’m bringing in our crisis specialist so you don’t have to face this alone."
            )
            state = self.add_message(state, "assistant", emergency_reply)
            state.agent_data["intake_stage"] = self.STAGE_READY_FOR_ASSESSMENT
            state.agent_data["intake_complete"] = True
            state.agent_data["force_crisis"] = True
            state.agent_data["skip_privacy_prompt"] = True
            self.log_decision(
                "intake_emergency_detected",
                {"trigger_message": last_user_message.content}
            )
            return state

        # Get conversation history
        messages: list = []

        # Add system prompt (true system instruction)
        messages.append(SystemMessage(content=self.get_system_prompt()))

        # Add stage-specific guidance as system context
        stage_guidance = self._get_stage_guidance(current_stage, state)
        if stage_guidance:
            messages.append(SystemMessage(content=stage_guidance))

        # Add conversation history after guidance
        messages.extend(state.messages)

        # Generate response
        logger.debug("🤖 Generating warm response...")
        response = await self.llm.ainvoke(messages)

        reply_text = self._extract_reply(response.content)

        # Determine next stage based on conversation (without AI reply yet)
        next_stage_preview = self._determine_next_stage(current_stage, state)

        if (
            next_stage_preview == self.STAGE_READY_FOR_ASSESSMENT
            and not state.agent_data.get("force_crisis")
        ):
            reply_text = self._build_transition_message(state)

        # Add response to state
        state = self.add_message(state, "assistant", reply_text)

        # Determine next stage based on conversation
        next_stage = self._determine_next_stage(current_stage, state)
        state.agent_data["intake_stage"] = next_stage

        logger.info(f"✅ Intake conversation progressing: {current_stage} → {next_stage}")

        if next_stage == self.STAGE_READY_FOR_ASSESSMENT and self._has_sufficient_context(state):
            state.agent_data["intake_complete"] = True
            logger.info("🎯 Intake complete - Ready for crisis assessment")
        else:
            state.agent_data.pop("intake_complete", None)

        return state

    def _extract_reply(self, raw_content: str) -> str:
        """
        Parse model output to retrieve the user-facing reply.

        The prompt forces JSON {"reply": "..."}; we parse and return the text.
        If parsing fails, fall back to the last non-empty line.
        """
        content = (raw_content or "").strip()

        if not content:
            return "I'm here with you. Tell me more about how today feels."

        # Prefer the final non-empty line to avoid stray reasoning.
        for line in reversed(content.splitlines()):
            cleaned = line.strip()
            if cleaned:
                return cleaned

        return content or "I'm here with you. Tell me more about how today feels."

    def _get_stage_guidance(self, stage: str, state: AgentState) -> Optional[str]:
        """
        Provide internal guidance to LLM based on current stage.

        This is NOT shown to user - it guides the LLM's response.
        """

        # Minimal guidance - trust the model to be smart
        guidance = {
            self.STAGE_GREETING: "Greet them warmly.",
            self.STAGE_CHECK_IN: "Ask how they're feeling.",
            self.STAGE_WHAT_BRINGS_YOU: "Ask what brought them here today.",
            self.STAGE_EXPLORE_TROUBLE: "Explore their main concern.",
            self.STAGE_GATHER_CONTEXT: "Learn more about their situation.",
            self.STAGE_READY_FOR_ASSESSMENT: "Offer to connect them with a volunteer therapist.",
        }

        return guidance.get(stage)

    def _determine_next_stage(self, current_stage: str, state: AgentState) -> str:
        """
        Determine next conversation stage based on user responses.

        This analyzes how much information we've gathered and
        moves to next stage appropriately.
        """

        # Count meaningful user messages (not just greetings)
        user_messages = [
            msg for msg in state.messages
            if hasattr(msg, 'type') and msg.type == 'human'
        ]

        num_exchanges = len(user_messages)

        # Simple progression: move to next agent after 4-5 turns MAX
        if num_exchanges >= 5:
            return self.STAGE_READY_FOR_ASSESSMENT

        if num_exchanges >= 4:
            return self.STAGE_READY_FOR_ASSESSMENT

        # Early stages - quick progression
        if current_stage == self.STAGE_GREETING and num_exchanges >= 1:
            return self.STAGE_CHECK_IN

        elif current_stage == self.STAGE_CHECK_IN and num_exchanges >= 2:
            return self.STAGE_WHAT_BRINGS_YOU

        elif current_stage == self.STAGE_WHAT_BRINGS_YOU and num_exchanges >= 3:
            return self.STAGE_EXPLORE_TROUBLE

        # Default: stay in current stage
        return current_stage

    def should_proceed_to_crisis_assessment(self, state: AgentState) -> bool:
        """
        Check if intake is complete and ready for crisis assessment.

        Returns:
            True if we've gathered enough information and built rapport
        """
        return bool(state.agent_data.get("intake_complete")) and self._has_sufficient_context(state)

    def get_gathered_context(self, state: AgentState) -> str:
        """
        Extract the context gathered during intake for crisis assessment.

        This summarizes what we learned about the user's situation.
        """

        # Get all user messages
        user_messages = [
            msg.content for msg in state.messages
            if hasattr(msg, 'type') and msg.type == 'human'
        ]

        # Combine into context summary
        context = "\n".join([f"User: {msg}" for msg in user_messages])

        return context

    def _has_sufficient_context(self, state: AgentState) -> bool:
        """
        Confirm intake gathered enough meaningful information before escalation.
        """

        user_messages = [
            msg.content for msg in state.messages
            if hasattr(msg, 'type') and msg.type == 'human'
        ]

        if state.agent_data.get("force_crisis"):
            return True

        if len(user_messages) >= 3:
            recent_text = " ".join(user_messages[-3:]).lower()
            if len(recent_text.split()) >= 20:
                return True

        if len(user_messages) < 4:
            return False

        recent_text = " ".join(user_messages[-4:]).lower()

        has_emotion = any(keyword in recent_text for keyword in self.EMOTION_KEYWORDS)
        has_support_request = any(keyword in recent_text for keyword in self.SUPPORT_KEYWORDS)
        word_count = len(recent_text.split())

        if has_emotion and has_support_request and word_count >= 30:
            return True

        return word_count >= 40

    def _get_last_user_message(self, state: AgentState) -> Optional[BaseMessage]:
        """
        Return the most recent human message, if any.
        """

        for message in reversed(state.messages):
            if getattr(message, "type", "") == "human":
                return message
        return None

    def _contains_immediate_risk(self, text: str) -> bool:
        """
        Quick heuristic for suicidal or self-harm language.
        """

        lowered = (text or "").lower()
        return any(keyword in lowered for keyword in self.CRISIS_KEYWORDS)

    def _build_transition_message(self, state: AgentState) -> str:
        """
        Generate a concise transition message to crisis workflow.
        """

        recent_user_message = self._get_last_user_message(state)
        if recent_user_message and getattr(recent_user_message, "content", "").strip():
            return (
                "Thank you for trusting me with that. It matters that you shared it out loud. "
                "Let me connect you with our crisis specialist right now so you get one-on-one support, "
                "and we’ll pick the privacy level that feels safest for you."
            )

        return (
            "Thank you for opening up. I’m going to bring in our crisis specialist to stay with you and we’ll choose the privacy "
            "setting that feels right before they join."
        )


# Convenience function for testing
async def test_intake_flow():
    """Test the intake agent's conversational flow."""

    print("\n" + "=" * 70)
    print("🤝 Testing Intake Agent - Warm Conversational Flow")
    print("=" * 70)
    print()

    agent = IntakeAgent()

    # Simulate multi-turn conversation
    state = AgentState(
        user_id="test_intake_user",
        privacy_tier="full_support"
    )

    # Turn 1: User initiates
    print("👤 User: Hi")
    state = agent.add_message(state, "user", "Hi")
    state = await agent.process(state)
    print(f"🤖 Intake Agent: {state.messages[-1].content}\n")

    # Turn 2: User responds to how are you
    print("👤 User: Not great honestly")
    state = agent.add_message(state, "user", "Not great honestly")
    state = await agent.process(state)
    print(f"🤖 Intake Agent: {state.messages[-1].content}\n")

    # Turn 3: User shares what brought them
    print("👤 User: I've been feeling really anxious lately and don't know what to do")
    state = agent.add_message(state, "user", "I've been feeling really anxious lately and don't know what to do")
    state = await agent.process(state)
    print(f"🤖 Intake Agent: {state.messages[-1].content}\n")

    # Turn 4: User explores more
    print("👤 User: It's been getting worse over the past few weeks. I can't sleep and I'm constantly worried.")
    state = agent.add_message(state, "user", "It's been getting worse over the past few weeks. I can't sleep and I'm constantly worried.")
    state = await agent.process(state)
    print(f"🤖 Intake Agent: {state.messages[-1].content}\n")

    # Turn 5: More context
    print("👤 User: I haven't tried anything yet. That's why I'm here.")
    state = agent.add_message(state, "user", "I haven't tried anything yet. That's why I'm here.")
    state = await agent.process(state)
    print(f"🤖 Intake Agent: {state.messages[-1].content}\n")

    # Check if ready for assessment
    if agent.should_proceed_to_crisis_assessment(state):
        print("=" * 70)
        print("✅ INTAKE COMPLETE - Ready for crisis assessment")
        print("=" * 70)
        print("\nGathered Context:")
        print(agent.get_gathered_context(state))

    print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_intake_flow())
