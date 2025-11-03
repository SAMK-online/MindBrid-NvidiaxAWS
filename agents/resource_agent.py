"""
Resource Agent - Autonomous Therapist Finding & Onboarding
===========================================================

This agent demonstrates ADVANCED agentic behavior:
1. Checks database for available therapists
2. If none available → Autonomously searches with Tavily
3. Reaches out to therapists via email (mocked for demo)
4. Adds therapists to database WITHOUT human intervention
5. Matches user with best-fit therapist

This is TRUE AGENCY - the system solves problems autonomously!
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from tavily import TavilyClient
from loguru import logger

from agents.base_agent import BaseAgent, AgentState
from models.therapist import Therapist, TimeSlot, TherapistSpecialization
from models.mock_data import therapist_db


# Tool: Check database for available therapists
@tool
def check_therapist_database(
    specialization: Optional[str] = None
) -> Dict[str, Any]:
    """Check database for available therapists with optional specialization filter."""

    # Convert string to enum if provided
    spec_filter = None
    if specialization:
        try:
            spec_filter = TherapistSpecialization(specialization.lower())
        except ValueError:
            logger.warning(f"Unknown specialization: {specialization}")

    # Query database
    available = therapist_db.get_available_therapists(specialization=spec_filter)

    # Get stats
    stats = therapist_db.get_statistics()

    logger.info(
        f"Database query: {len(available)} available",
        extra={"specialization": specialization, "available_count": len(available)}
    )

    return {
        "available_count": len(available),
        "therapists": [
            {
                "id": t.id,
                "name": t.name,
                "specializations": [s.value for s in t.specializations],
                "years_experience": t.years_experience,
                "current_load": f"{t.current_patients}/{t.max_patients}",
                "availability_slots": len(t.time_slots)
            }
            for t in available
        ],
        "database_stats": stats,
        "search_needed": len(available) == 0
    }


# Tool: Search web for therapist directories
@tool
async def search_therapist_directories(
    location: str = "United States",
    specialization: Optional[str] = None
) -> Dict[str, Any]:
    """Search web for therapist directories and contact information."""

    # Build search query
    query_parts = ["mental health therapist", "volunteer", "contact information"]

    if specialization:
        query_parts.insert(0, specialization)

    if location != "United States":
        query_parts.append(location)

    search_query = " ".join(query_parts)

    logger.info(f"🌐 Searching Tavily: {search_query}")

    try:
        # Initialize Tavily client
        import os
        tavily_key = os.getenv("TAVILY_API_KEY")
        tavily = TavilyClient(api_key=tavily_key)

        # Perform search
        results = tavily.search(
            query=search_query,
            max_results=5,
            search_depth="advanced"
        )

        # Extract relevant information
        found_resources = []
        for result in results.get('results', []):
            found_resources.append({
                "title": result.get('title'),
                "url": result.get('url'),
                "content_snippet": result.get('content', '')[:200],
                "relevance_score": result.get('score', 0)
            })

        logger.info(f"✅ Found {len(found_resources)} resources via Tavily")

        return {
            "search_query": search_query,
            "results_found": len(found_resources),
            "resources": found_resources,
            "search_successful": len(found_resources) > 0
        }

    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return {
            "search_query": search_query,
            "results_found": 0,
            "resources": [],
            "search_successful": False,
            "error": str(e)
        }


# Tool: Mock outreach to therapists
@tool
def outreach_to_therapists(
    therapist_contacts: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Reach out to potential therapists via email (mocked for demo).

    In production, this would:
    - Send actual emails via SendGrid/AWS SES
    - Track responses
    - Update database with status

    For demo, we simulate successful outreach.
    """

    logger.info(f"📧 Reaching out to {len(therapist_contacts)} therapists")

    # Mock email template
    email_template = """
    Subject: Join MindBridge AI - Help People Access Mental Health Care

    Dear {name},

    We found your practice while searching for mental health professionals
    who might be interested in volunteering with MindBridge AI.

    MindBridge connects people who can't afford therapy with volunteer
    therapists like you. We handle all the scheduling and provide an
    AI assistant to help with administrative tasks.

    Would you be interested in volunteering a few hours per month?

    Learn more: https://mindbridge.ai/volunteer

    Best regards,
    MindBridge AI Team
    """

    # Simulate sending emails
    sent_emails = []
    for contact in therapist_contacts[:3]:  # Limit to 3 for demo
        sent_emails.append({
            "recipient": contact.get("email", "unknown@example.com"),
            "name": contact.get("name", "Therapist"),
            "status": "sent",
            "sent_at": datetime.now().isoformat()
        })

    logger.info(f"✅ Sent {len(sent_emails)} outreach emails")

    return {
        "emails_sent": len(sent_emails),
        "outreach_list": sent_emails,
        "template_used": "volunteer_invitation",
        "follow_up_scheduled": True
    }


# Tool: Add therapist to database
@tool
def add_therapist_to_database(
    therapist_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add a newly found therapist to the database.

    This is called AUTONOMOUSLY when the agent finds new therapists!
    """

    try:
        # Create therapist object
        # For demo, we'll create a basic profile
        # In production, this would come from therapist signup form

        new_therapist = Therapist(
            id=f"therapist_{uuid.uuid4().hex[:8]}",
            name=therapist_info.get("name", "New Therapist"),
            email=therapist_info.get("email", "new@mindbridge.org"),
            specializations=[TherapistSpecialization.GENERAL],  # Default
            years_experience=therapist_info.get("years_experience", 5),
            time_slots=[],  # Will be filled in after onboarding
            is_volunteer=True,
            status="pending",  # Pending confirmation
            max_patients=10,
            current_patients=0,
            bio=therapist_info.get("bio", "Newly added therapist")
        )

        # Add to database
        success = therapist_db.add_therapist(new_therapist)

        if success:
            logger.info(f"✅ Added {new_therapist.name} to database")
            return {
                "success": True,
                "therapist_id": new_therapist.id,
                "therapist_name": new_therapist.name,
                "status": "pending_confirmation"
            }
        else:
            return {
                "success": False,
                "error": "Therapist already exists"
            }

    except Exception as e:
        logger.error(f"Failed to add therapist: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Tool: Match user with best therapist
@tool
def match_user_with_therapist(
    user_needs: Dict[str, Any],
    available_therapists: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Match user with best-fit therapist based on:
    - Specialization match
    - Availability
    - Experience level
    - Current patient load
    """

    if not available_therapists:
        return {
            "match_found": False,
            "reason": "No therapists available"
        }

    # Simple scoring algorithm
    # In production, this would be more sophisticated

    user_specialization = user_needs.get("specialization", "general")

    scored_therapists = []
    for therapist in available_therapists:
        score = 0

        # Specialization match (most important)
        if user_specialization in therapist.get("specializations", []):
            score += 50

        # Experience (more is better)
        score += min(therapist.get("years_experience", 0), 20)

        # Availability (fewer patients = more availability)
        current, max_patients = map(int, therapist.get("current_load", "0/10").split('/'))
        availability_pct = 100 - ((current / max_patients) * 100)
        score += availability_pct * 0.3

        scored_therapists.append({
            **therapist,
            "match_score": score
        })

    # Sort by score
    scored_therapists.sort(key=lambda x: x["match_score"], reverse=True)

    best_match = scored_therapists[0]

    logger.info(
        f"✅ Matched user with {best_match['name']}",
        extra={"score": best_match["match_score"]}
    )

    return {
        "match_found": True,
        "therapist": best_match,
        "match_score": best_match["match_score"],
        "alternatives": scored_therapists[1:3]  # Top 3
    }


# Main Resource Agent
class ResourceAgent(BaseAgent):
    """
    Autonomous therapist finding and matching agent.

    Demonstrates true agency through:
    - Autonomous problem-solving (no therapists? search for them!)
    - Proactive outreach (contacts therapists automatically)
    - Database management (adds therapists without human intervention)
    - Intelligent matching (finds best fit for user)
    """

    def __init__(self):
        super().__init__(
            agent_name="Resource Agent",
            temperature=0.4,  # Balance between consistency and adaptability
            max_tokens=1024,
        )

        # Bind tools to LLM
        self.tools = [
            check_therapist_database,
            search_therapist_directories,
            outreach_to_therapists,
            add_therapist_to_database,
            match_user_with_therapist
        ]

        self.llm_with_tools = self.llm.bind_tools(self.tools)

        logger.info("🔍 Resource Agent initialized with autonomous search capabilities")


    def get_system_prompt(self) -> str:
        """System prompt defining Resource Agent behavior."""

        return """You are the Resource Agent for MindBridge AI mental health platform.

Your mission: Connect users with appropriate therapists autonomously.

WORKFLOW (ReAct Pattern):
1. THOUGHT: What does the user need?
2. ACTION: check_therapist_database(specialization)
3. OBSERVATION: Are therapists available?

IF YES:
4. ACTION: match_user_with_therapist()
5. RESPONSE: "I found Dr. [Name] who specializes in [X]..."

IF NO (THIS IS WHERE YOU SHOW AUTONOMY):
4. THOUGHT: No therapists available - I need to find some!
5. ACTION: search_therapist_directories()
6. OBSERVATION: Found therapist directories/contacts
7. THOUGHT: I should reach out to these therapists
8. ACTION: outreach_to_therapists()
9. OBSERVATION: Emails sent
10. ACTION: add_therapist_to_database() for each
11. RESPONSE: "I've reached out to 3 therapists and added them to our system.
              In the meantime, here are crisis resources..."

IMPORTANT:
- Be proactive - don't wait for humans to solve problems
- Show your reasoning (the demo needs to see your thought process)
- Be empathetic when explaining delays
- Always provide crisis resources if no immediate match

Tools available:
- check_therapist_database: Query available therapists
- search_therapist_directories: Find new therapists via web search
- outreach_to_therapists: Contact therapists autonomously
- add_therapist_to_database: Onboard new therapists
- match_user_with_therapist: Find best fit
"""


    async def process(self, state: AgentState) -> AgentState:
        """
        Main processing loop - finds and matches therapists autonomously.

        This demonstrates REAL AGENCY:
        - Makes decisions without human input
        - Takes actions to solve problems
        - Adapts strategy based on observations
        """

        # Extract user needs from state
        user_needs = state.agent_data.get("user_needs", {})
        specialization = user_needs.get("specialization", None)

        logger.info(
            f"🔍 Finding therapist",
            extra={"specialization": specialization}
        )

        # Build conversation for LLM
        messages = [
            SystemMessage(content=self.get_system_prompt())
        ]

        # Add context about user needs
        context_message = HumanMessage(
            content=f"A user needs a therapist. "
                   f"Specialization needed: {specialization or 'general support'}. "
                   f"Find an available therapist or autonomously source new ones."
        )
        messages.append(context_message)

        # Add recent conversation
        recent_messages = self.get_conversation_history(state, max_messages=3)
        messages.extend(recent_messages)


        # ReAct Loop - Let agent decide what to do
        max_iterations = 8  # More iterations for complex workflow
        iteration = 0

        therapist_found = None

        while iteration < max_iterations:
            iteration += 1

            logger.debug(f"🧠 Resource Agent iteration {iteration}/{max_iterations}")

            # Call LLM with tools
            response = await self.llm_with_tools.ainvoke(messages)
            messages.append(response)

            # Check for tool calls (ReAct ACTION phase)
            if hasattr(response, 'tool_calls') and response.tool_calls:

                logger.info(f"🛠️  Agent calling {len(response.tool_calls)} tool(s)")

                # Execute each tool
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']

                    logger.debug(f"   └─ {tool_name}({tool_args})")

                    # Execute tool
                    tool_result = await self._execute_tool(tool_name, tool_args)

                    # Add result to conversation (ReAct OBSERVATION phase)
                    messages.append(
                        HumanMessage(
                            content=f"Tool '{tool_name}' returned: {tool_result}"
                        )
                    )

                    # Log for demo visualization
                    self.log_decision(
                        f"tool_{tool_name}",
                        {
                            "args": tool_args,
                            "result": tool_result
                        }
                    )

                    # Check if we found a match
                    if tool_name == "match_user_with_therapist":
                        if tool_result.get("match_found"):
                            therapist_found = tool_result.get("therapist")

                # Continue loop
                continue

            else:
                # No more tools - agent has final response
                logger.info("✅ Resource matching complete")

                final_response = response.content

                # Add to state
                state = self.add_message(state, "assistant", final_response)

                # Store matched therapist in state if found
                if therapist_found:
                    state = self.update_agent_data(
                        state,
                        "matched_therapist",
                        therapist_found
                    )

                # Log completion
                self.log_decision(
                    "resource_matching_complete",
                    {
                        "iterations": iteration,
                        "therapist_found": therapist_found is not None,
                        "therapist_name": therapist_found.get("name") if therapist_found else None
                    }
                )

                break

        return state


    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """Execute a tool by name."""

        tool_map = {
            "check_therapist_database": check_therapist_database,
            "search_therapist_directories": search_therapist_directories,
            "outreach_to_therapists": outreach_to_therapists,
            "add_therapist_to_database": add_therapist_to_database,
            "match_user_with_therapist": match_user_with_therapist
        }

        if tool_name not in tool_map:
            logger.error(f"Unknown tool: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            tool_func = tool_map[tool_name]

            # Check if tool is async
            if tool_name == "search_therapist_directories":
                result = await tool_func.ainvoke(tool_args)
            else:
                result = tool_func.invoke(tool_args)

            return result

        except Exception as e:
            logger.error(f"Tool '{tool_name}' failed: {e}")
            return {"error": str(e)}


# Example usage for testing
if __name__ == "__main__":
    import asyncio

    async def test_resource_agent():
        """Test the Resource Agent's autonomous behavior."""

        print("=" * 70)
        print("🔍 Resource Agent - Autonomous Therapist Finding Test")
        print("=" * 70)
        print()

        # Create agent
        agent = ResourceAgent()

        # Create state with user needs
        state = AgentState(
            user_id="test_user",
            privacy_tier="full_support"
        )

        # Simulate user asking for therapist with anxiety specialization
        state = agent.add_message(
            state,
            "user",
            "I need help with my anxiety. Can you connect me with a therapist?"
        )

        # Add user needs to state
        state = agent.update_agent_data(
            state,
            "user_needs",
            {"specialization": "anxiety"}
        )

        # Process with agent
        print("🔄 Processing request (watch for autonomous behavior)...")
        print()

        state = await agent.process(state)

        # Show results
        print("\n" + "=" * 70)
        print("📊 Results")
        print("=" * 70)
        print()

        if len(state.messages) >= 2:
            response = state.messages[-1].content
            print(f"🤖 Agent Response:\n{response}\n")

        matched = state.agent_data.get("matched_therapist")
        if matched:
            print(f"✅ Matched with: {matched.get('name')}")
            print(f"   Specializations: {', '.join(matched.get('specializations', []))}")
            print(f"   Match Score: {matched.get('match_score', 0):.1f}")

        print()

    asyncio.run(test_resource_agent())
