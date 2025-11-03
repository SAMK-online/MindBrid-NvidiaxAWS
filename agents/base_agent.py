"""
Base Agent Class - Foundation for All MindBridge Agents
========================================================

This is the base class that ALL agents inherit from. It provides:
1. LLM connection (NVIDIA Nemotron via OpenRouter)
2. Logging for demo visualization
3. State management utilities
4. Error handling
5. Common tools

WHY USE A BASE CLASS?
---------------------
Instead of repeating LLM setup in every agent, we write it ONCE here.
All child agents (Crisis, Habit, Resource) automatically get these features.

DESIGN PATTERN: Template Method Pattern
- Base class defines the skeleton
- Child classes fill in specific behaviors
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ================================================================
# AGENT STATE MODELS
# ================================================================
# These Pydantic models define the "memory" each agent works with

class AgentState(BaseModel):
    """
    Base state that all agents use.

    Think of this as the agent's "working memory" - what information
    it has access to while making decisions.

    Why Pydantic?
    - Type validation (catches bugs early)
    - Automatic serialization (easy to save/load)
    - Self-documenting (clear what data agents need)
    """

    # Conversation history - critical for context
    messages: List[BaseMessage] = Field(
        default_factory=list,
        description="Full conversation history with user"
    )

    # User context - who are we helping?
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier (respects privacy tiers)"
    )

    # Privacy tier - how much AI assistance is allowed?
    privacy_tier: str = Field(
        default="your_private_notes",
        description="One of: no_records, your_private_notes, assisted_handoff, full_support"
    )

    # Metadata - useful for tracking and debugging
    session_id: Optional[str] = Field(
        default=None,
        description="Unique session identifier"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this state was created/updated"
    )

    # Agent-specific data - each agent can add custom fields
    agent_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom data storage for specific agents"
    )


# ================================================================
# BASE AGENT CLASS
# ================================================================

class BaseAgent(ABC):
    """
    Abstract base class for all MindBridge agents.

    All agents (Crisis, Habit, Resource) inherit from this class
    and get common functionality automatically.

    ABSTRACT CLASS means:
    - You can't create a BaseAgent directly (only CrisisAgent, etc.)
    - Child classes MUST implement certain methods (marked @abstractmethod)
    """

    def __init__(
        self,
        agent_name: str,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        """
        Initialize the base agent.

        Args:
            agent_name: Name of this agent (e.g., "Crisis Agent", "Habit Agent")
                       Used for logging and debugging

            model_name: Which Nemotron model to use
                       Default: nano-9b for focused agents
                       Can override to use super-49b for coordination

            temperature: How creative/random the model should be
                        0.0 = Deterministic, always same answer
                        1.0 = Very creative, varied answers
                        0.7 = Good balance for mental health (empathetic but consistent)

            max_tokens: Maximum response length
                       Prevents runaway responses
                       2048 tokens ≈ 1500 words
        """

        self.agent_name = agent_name
        self.model_name = model_name or os.getenv(
            "AGENT_MODEL",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5"
        )
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize core components
        self._setup_logging()
        self._initialize_llm()

        logger.info(
            f"🤖 {self.agent_name} initialized",
            extra={
                "model": self.model_name,
                "temperature": self.temperature,
            }
        )

    # ----------------------------------------------------------------
    # LOGGING SETUP
    # ----------------------------------------------------------------

    def _setup_logging(self) -> None:
        """
        Configure logging for this agent.

        WHY LOGGING IS CRITICAL:
        1. Demo visualization - Show judges agent reasoning
        2. Debugging - Track down issues quickly
        3. Monitoring - Understand agent behavior in production

        Loguru features we use:
        - Colored output for readability
        - Structured logging (JSON-compatible)
        - Automatic rotation (prevents huge log files)
        """

        # Configure loguru format
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[agent_name]}</cyan> | "
            "<level>{message}</level>"
        )

        # Add agent name to all log messages
        logger.configure(
            extra={"agent_name": self.agent_name}
        )

        # For demo: We'll also log to a file for later analysis
        # logger.add(
        #     f"logs/{self.agent_name.lower().replace(' ', '_')}.log",
        #     rotation="10 MB",  # Create new file when it reaches 10MB
        #     retention="7 days",  # Keep logs for a week
        #     format=log_format,
        # )

    # ----------------------------------------------------------------
    # LLM INITIALIZATION
    # ----------------------------------------------------------------

    def _initialize_llm(self) -> None:
        """
        Set up connection to NVIDIA Nemotron via OpenRouter.

        This is the CORE of our agentic system - the LLM that makes decisions.

        WHY THESE SETTINGS?
        - base_url: Points to OpenRouter (our gateway to Nemotron)
        - model: Nemotron Nano 9B (fast, efficient for focused tasks)
        - temperature: 0.7 (empathetic but consistent)
        - max_tokens: Prevents excessive responses
        """

        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not found in environment. "
                "Please set it in your .env file."
            )

        try:
            self.llm = ChatNVIDIA(
                base_url="https://openrouter.ai/api/v1",
                model=self.model_name,
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            logger.debug(f"✅ LLM initialized: {self.model_name}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM: {e}")
            raise

    # ----------------------------------------------------------------
    # CORE AGENT METHODS (Must be implemented by child classes)
    # ----------------------------------------------------------------

    @abstractmethod
    async def process(self, state: AgentState) -> AgentState:
        """
        Main processing method - MUST be implemented by each agent.

        This is where the agent's core logic lives:
        - Crisis Agent: Assess risk level
        - Habit Agent: Check progress, decide intervention
        - Resource Agent: Search for therapists

        Args:
            state: Current agent state (conversation, user data, etc.)

        Returns:
            Updated state with agent's actions/decisions

        WHY ASYNC?
        - Agents often need to wait for LLM responses
        - Async allows other agents to work concurrently
        - Critical for real-time responsiveness
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Return the system prompt for this agent.

        The system prompt defines the agent's:
        - Role (e.g., "You are a crisis assessment specialist")
        - Capabilities (e.g., "You can assess suicide risk")
        - Constraints (e.g., "Never provide medical advice")
        - Personality (e.g., "Be empathetic and non-judgmental")

        Each agent has a different prompt that shapes its behavior.
        """
        pass

    # ----------------------------------------------------------------
    # HELPER METHODS (Shared by all agents)
    # ----------------------------------------------------------------

    async def invoke_llm(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AIMessage:
        """
        Call the LLM with error handling and logging.

        This wraps the raw LLM call with:
        1. Logging (for demo visualization)
        2. Error handling (graceful failures)
        3. Metrics (track usage)

        Args:
            messages: Conversation history to send to LLM
            **kwargs: Additional parameters (temperature override, etc.)

        Returns:
            LLM's response as an AIMessage
        """

        try:
            logger.debug(
                f"🧠 Calling LLM with {len(messages)} messages",
                extra={"message_count": len(messages)}
            )

            # Make the actual LLM call
            response = await self.llm.ainvoke(messages, **kwargs)

            logger.debug(
                f"✅ LLM responded",
                extra={
                    "response_length": len(response.content),
                }
            )

            return response

        except Exception as e:
            logger.error(f"❌ LLM call failed: {e}")

            # Return a fallback message instead of crashing
            return AIMessage(
                content="I apologize, but I'm having trouble processing right now. "
                       "Please try again in a moment."
            )

    def add_message(
        self,
        state: AgentState,
        role: str,
        content: str
    ) -> AgentState:
        """
        Add a message to the conversation history.

        Utility method to maintain conversation state.

        Args:
            state: Current agent state
            role: Who's speaking ("user", "assistant", "system")
            content: What they said

        Returns:
            Updated state with new message
        """

        # Create the appropriate message type
        if role == "user":
            message = HumanMessage(content=content)
        elif role == "assistant":
            message = AIMessage(content=content)
        elif role == "system":
            message = SystemMessage(content=content)
        else:
            raise ValueError(f"Unknown role: {role}")

        # Add to state
        state.messages.append(message)

        logger.debug(
            f"💬 Added {role} message",
            extra={"role": role, "length": len(content)}
        )

        return state

    def get_conversation_history(
        self,
        state: AgentState,
        max_messages: Optional[int] = None
    ) -> List[BaseMessage]:
        """
        Retrieve conversation history, optionally limiting to recent messages.

        WHY LIMIT MESSAGES?
        - LLMs have context window limits (max tokens they can process)
        - Older messages may be less relevant
        - Reduces API costs

        Args:
            state: Current agent state
            max_messages: If set, only return last N messages

        Returns:
            List of messages (recent first if limited)
        """

        if max_messages is None:
            return state.messages

        return state.messages[-max_messages:]

    def log_decision(
        self,
        decision_type: str,
        details: Dict[str, Any]
    ) -> None:
        """
        Log an agent decision for demo visualization.

        This is CRITICAL for the hackathon demo - judges need to see
        the agent's reasoning process, not just the final output.

        Example:
            self.log_decision(
                "risk_assessment",
                {
                    "risk_level": "moderate",
                    "reasoning": "User mentioned feeling hopeless",
                    "action": "escalate_to_resource_agent"
                }
            )

        Args:
            decision_type: Category of decision
            details: Structured data about the decision
        """

        logger.info(
            f"🎯 Decision: {decision_type}",
            extra={
                "decision_type": decision_type,
                **details
            }
        )

    # ----------------------------------------------------------------
    # STATE MANAGEMENT
    # ----------------------------------------------------------------

    def update_agent_data(
        self,
        state: AgentState,
        key: str,
        value: Any
    ) -> AgentState:
        """
        Store agent-specific data in the state.

        Each agent can use this to persist information between calls.

        Example (Habit Agent):
            state = self.update_agent_data(
                state,
                "last_check_time",
                datetime.now()
            )

        Args:
            state: Current state
            key: Data key
            value: Data value

        Returns:
            Updated state
        """

        state.agent_data[key] = value
        return state

    def get_agent_data(
        self,
        state: AgentState,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Retrieve agent-specific data from state.

        Args:
            state: Current state
            key: Data key
            default: Value to return if key doesn't exist

        Returns:
            Stored value or default
        """

        return state.agent_data.get(key, default)


# ================================================================
# USAGE EXAMPLE (for documentation)
# ================================================================

"""
Example: Creating a Child Agent

```python
from agents.base_agent import BaseAgent, AgentState

class MyCustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="My Custom Agent",
            temperature=0.8,  # More creative
        )

    async def process(self, state: AgentState) -> AgentState:
        # Add system prompt
        messages = [
            SystemMessage(content=self.get_system_prompt())
        ]

        # Add conversation history
        messages.extend(state.messages)

        # Get LLM response
        response = await self.invoke_llm(messages)

        # Log the decision
        self.log_decision(
            "custom_action",
            {"reasoning": "Because I decided so!"}
        )

        # Add response to state
        state = self.add_message(state, "assistant", response.content)

        return state

    def get_system_prompt(self) -> str:
        return "You are a helpful assistant specialized in..."
```
"""
