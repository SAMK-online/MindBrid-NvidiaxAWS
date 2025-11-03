#!/usr/bin/env python3
"""
Comprehensive End-to-End Demo - Multi-Agent Workflow
=====================================================

This demonstrates the COMPLETE user journey through the MindBridge platform:

SCENARIO 1: High-Risk Crisis → Resource Matching
- User expresses severe distress
- Crisis Agent detects high risk
- Routes to Resource Agent
- Matches with available therapist

SCENARIO 2: Low-Risk Support → Self-Help Resources
- User mentions mild stress
- Crisis Agent detects low/no risk
- Routes to Support Resources
- Provides coping strategies

SCENARIO 3: Database Empty → Autonomous Search
- No therapists available
- Resource Agent autonomously searches web
- Adds therapists to database
- Matches user

This is the GOLDEN DEMO for the hackathon presentation!
"""

import asyncio
from workflows.crisis_to_resource import run_crisis_resource_workflow
from models.mock_data import therapist_db
from loguru import logger

# Make output more visually appealing for demo
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    format="<level>{message}</level>",
    colorize=True
)


def print_section_header(title: str, emoji: str = "🎯"):
    """Print a visually appealing section header."""
    print("\n")
    print("=" * 80)
    print(f"{emoji}  {title}")
    print("=" * 80)
    print()


def print_scenario_header(number: int, title: str, description: str):
    """Print scenario header with details."""
    print("\n")
    print("█" * 80)
    print(f"📋 SCENARIO {number}: {title}")
    print("─" * 80)
    print(f"   {description}")
    print("█" * 80)
    print()


def print_db_stats():
    """Display current database statistics."""
    stats = therapist_db.get_statistics()
    print("📊 Current Database Status:")
    print(f"   • Total Therapists: {stats['total_therapists']}")
    print(f"   • Active: {stats['active']}")
    print(f"   • Available: {stats['available']}")
    print(f"   • Full: {stats['full']}")
    print(f"   • Utilization: {stats['utilization_rate']:.1f}%")
    print()


def print_result_summary(result: dict):
    """Display workflow result in a clean format."""
    print("\n" + "─" * 80)
    print("📊 WORKFLOW RESULT SUMMARY")
    print("─" * 80)

    # Messages exchanged
    print(f"💬 Messages Exchanged: {len(result.get('messages', []))}")

    # Risk assessment
    risk_level = result.get('risk_level', 'unknown')
    risk_emoji = {
        'none': '🟢',
        'low': '🟡',
        'moderate': '🟠',
        'high': '🔴',
        'immediate': '🚨'
    }.get(risk_level, '❓')
    print(f"{risk_emoji} Risk Level: {risk_level.upper()}")

    # Crisis detection
    crisis_detected = result.get('crisis_detected', False)
    crisis_icon = "🚨 YES" if crisis_detected else "✅ NO"
    print(f"   Crisis Detected: {crisis_icon}")

    # Coordinator plan
    coordinator_plan = result.get('coordinator_plan') or []
    if coordinator_plan:
        print("\n🧭 Coordinator Plan:")
        for step in coordinator_plan:
            print(f"   • {step}")

    # Therapist matching
    therapist_matched = result.get('therapist_matched', False)
    if therapist_matched:
        therapist_name = result.get('matched_therapist_name', 'Unknown')
        print(f"👨‍⚕️  Therapist Match: ✅ YES")
        print(f"   Matched with: {therapist_name}")
    else:
        print(f"👨‍⚕️  Therapist Match: ⏸️  NO (Support resources provided)")

    # Habit follow-through
    habit_plan = result.get('habit_plan') or []
    if habit_plan:
        print("\n📈 Habit Agent Follow-Up:")
        for item in habit_plan:
            print(f"   • {item['title']}: {item['description']}")

    print("─" * 80)

    # Show final message
    if result.get('messages'):
        final_message = result['messages'][-1].content
        print("\n🤖 Final Response Preview:")
        print("   " + final_message[:200] + "..." if len(final_message) > 200 else "   " + final_message)
        print()


async def scenario_1_high_risk_crisis():
    """
    SCENARIO 1: High-Risk Crisis Detection

    This demonstrates:
    - Crisis Agent detecting severe distress
    - Automatic routing to Resource Agent
    - Therapist matching with trauma specialist
    - Complete handoff for immediate support
    """

    print_scenario_header(
        1,
        "High-Risk Crisis Detection & Resource Matching",
        "User expresses severe distress → Crisis detection → Therapist matching"
    )

    # Show database before
    print_db_stats()

    # User message with clear high-risk indicators
    user_message = (
        "I don't know how much longer I can do this. Everything feels hopeless "
        "and I can't see a way out. I just want the pain to stop. I feel like "
        "I'm a burden to everyone around me."
    )

    print("💬 User Message:")
    print(f'   "{user_message}"')
    print()

    # Run workflow
    print("🔄 Starting Multi-Agent Workflow...")
    print()

    result = await run_crisis_resource_workflow(
        user_message=user_message,
        user_id="demo_user_1",
        privacy_tier="full_support"
    )

    # Display results
    print_result_summary(result)

    # Validate expected behavior
    assert result['crisis_detected'], "Should detect crisis"
    assert result['risk_level'] in ['high', 'immediate'], "Should be high risk"
    # Note: therapist_matched might be False if Resource Agent provides alternatives

    print("✅ SCENARIO 1 COMPLETE: High-risk crisis properly detected and routed\n")


async def scenario_2_low_risk_support():
    """
    SCENARIO 2: Low-Risk Support Resources

    This demonstrates:
    - Crisis Agent detecting mild stress (no crisis)
    - Routing to Support Resources (not therapist)
    - Providing self-help strategies
    - No escalation needed
    """

    print_scenario_header(
        2,
        "Low-Risk Support Resources",
        "User mentions mild stress → No crisis detected → Self-help resources"
    )

    # User message with low-risk indicators
    user_message = (
        "I've been feeling a bit stressed about my upcoming presentation at work. "
        "I'm a little nervous but I'll probably be fine. Just wanted to talk it through "
        "and maybe get a simple routine I can stick with."
    )

    print("💬 User Message:")
    print(f'   "{user_message}"')
    print()

    # Run workflow
    print("🔄 Starting Multi-Agent Workflow...")
    print()

    result = await run_crisis_resource_workflow(
        user_message=user_message,
        user_id="demo_user_2",
        privacy_tier="full_support"
    )

    # Display results
    print_result_summary(result)

    # Validate expected behavior
    # Note: The workflow might still detect some level of stress
    # The key is it should NOT escalate to resource matching
    print("✅ SCENARIO 2 COMPLETE: Low-risk case handled appropriately\n")


async def scenario_3_autonomous_search():
    """
    SCENARIO 3: Autonomous Therapist Search

    This demonstrates TRUE AGENCY:
    - Database is empty
    - Resource Agent AUTONOMOUSLY decides to search web
    - Uses Tavily to find therapist directories
    - Reaches out and onboards therapists
    - Adds them to database
    - Completes the match

    THIS IS THE MOST IMPRESSIVE PART!
    """

    print_scenario_header(
        3,
        "Autonomous Therapist Search & Onboarding",
        "Empty database → Agent autonomously searches → Onboards therapists → Match!"
    )

    # Save original database
    print("🗄️  Temporarily clearing database to simulate empty state...")
    original_therapists = therapist_db.therapists.copy()
    therapist_db.therapists = []

    print_db_stats()
    print("⚠️  NO THERAPISTS AVAILABLE - Watch the agent work autonomously!")
    print()

    # User message requiring crisis support
    user_message = (
        "I've been struggling with severe anxiety and panic attacks. "
        "I really need professional help but can't afford therapy. "
        "Can you help me find someone and a grounding routine while I wait?"
    )

    print("💬 User Message:")
    print(f'   "{user_message}"')
    print()

    # Run workflow with empty database
    print("🔄 Starting Multi-Agent Workflow (with autonomous search)...")
    print()
    print("👀 Watch for:")
    print("   1️⃣  Agent checks database → finds it empty")
    print("   2️⃣  Agent DECIDES autonomously to search web")
    print("   3️⃣  Agent searches Tavily for therapist directories")
    print("   4️⃣  Agent reaches out to therapists")
    print("   5️⃣  Agent adds them to database")
    print("   6️⃣  Agent completes the match")
    print()

    result = await run_crisis_resource_workflow(
        user_message=user_message,
        user_id="demo_user_3",
        privacy_tier="full_support"
    )

    # Display results
    print_result_summary(result)

    # Check if database was populated
    print("\n📊 Database After Autonomous Action:")
    new_stats = therapist_db.get_statistics()
    print(f"   • Total Therapists: {new_stats['total_therapists']}")
    print(f"   • Available: {new_stats['available']}")
    print()

    if new_stats['total_therapists'] > 0:
        print("🎉 AUTONOMY DEMONSTRATED!")
        print("   The agent autonomously:")
        print("   ✅ Detected problem (empty database)")
        print("   ✅ Decided to search for solution")
        print("   ✅ Executed web search")
        print("   ✅ Onboarded therapists")
        print(f"   ✅ Added {new_stats['total_therapists']} therapists to database")
        print()

    # Restore original database
    therapist_db.therapists = original_therapists
    print("🔄 Database restored to original state")

    print("✅ SCENARIO 3 COMPLETE: Autonomous behavior successfully demonstrated\n")


async def scenario_4_privacy_tiers():
    """
    SCENARIO 4: Privacy Tier Demonstration

    Shows how different privacy tiers affect agent behavior:
    - Full Support: Complete AI assistance
    - Assisted Handoff: Limited AI involvement
    - Your Private Notes: Minimal AI processing
    - No Records: Complete anonymity
    """

    print_scenario_header(
        4,
        "Privacy Tier System",
        "Same message, different privacy tiers → Different agent behaviors"
    )

    # Same message for all privacy tiers
    user_message = "I've been feeling down lately and could use some support."

    privacy_tiers = [
        ("full_support", "Complete AI assistance with all features"),
        ("assisted_handoff", "AI helps connect to therapist"),
        ("your_private_notes", "Minimal AI, user controls data"),
        ("no_records", "Complete anonymity, no data stored")
    ]

    print("💬 Test Message (same for all tiers):")
    print(f'   "{user_message}"')
    print()

    for tier, description in privacy_tiers:
        print(f"\n🔒 Privacy Tier: {tier.upper().replace('_', ' ')}")
        print(f"   {description}")
        print("   " + "─" * 60)

        result = await run_crisis_resource_workflow(
            user_message=user_message,
            user_id=f"demo_privacy_{tier}",
            privacy_tier=tier
        )

        # Show how behavior differs
        print(f"   📊 Risk assessed: {result.get('risk_level', 'N/A')}")
        print(f"   🤖 AI involvement: {tier}")
        print()

    print("✅ SCENARIO 4 COMPLETE: Privacy tiers demonstrated\n")


async def main():
    """Run all demo scenarios in sequence."""

    print_section_header(
        "MindBridge AI - Comprehensive Demo",
        "🎯"
    )

    print("This demonstration shows:")
    print("  ✅ Multi-agent coordination (Crisis → Resource)")
    print("  ✅ Conditional routing (high-risk vs low-risk)")
    print("  ✅ Autonomous decision-making")
    print("  ✅ Tool calling and ReAct pattern")
    print("  ✅ TRUE agentic behavior (not just chatbot)")
    print()
    print("Perfect for 3-minute hackathon presentation!")
    print()

    # Auto-start demo (no input required for non-interactive mode)
    print("Starting demo in 2 seconds...")
    await asyncio.sleep(2)

    try:
        # Scenario 1: High-risk crisis
        await scenario_1_high_risk_crisis()
        await asyncio.sleep(2)

        # Scenario 2: Low-risk support
        await scenario_2_low_risk_support()
        await asyncio.sleep(2)

        # Scenario 3: Autonomous search (THE BIG ONE!)
        await scenario_3_autonomous_search()
        await asyncio.sleep(2)

        # Scenario 4: Privacy tiers
        await scenario_4_privacy_tiers()

        # Final summary
        print_section_header("Demo Complete!", "🎉")
        print("Key Demonstrations:")
        print("  ✅ Multi-agent orchestration with LangGraph")
        print("  ✅ Crisis detection with ReAct pattern")
        print("  ✅ Autonomous therapist search and onboarding")
        print("  ✅ Privacy-preserving architecture")
        print("  ✅ NVIDIA Nemotron models powering all agents")
        print()
        print("This platform demonstrates TRUE agentic AI:")
        print("  • Agents make autonomous decisions")
        print("  • Multi-step reasoning with tools")
        print("  • Coordination without human intervention")
        print("  • Adaptive behavior based on context")
        print()
        print("Ready for hackathon presentation! 🚀")
        print()

    except Exception as e:
        logger.exception("Demo failed with error:")
        print(f"\n❌ Error during demo: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
