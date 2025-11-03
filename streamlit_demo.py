#!/usr/bin/env python3
"""
MindBridge AI - Streamlit Demo Interface
=========================================

Interactive demo for hackathon presentation.

Features:
- Split screen: Chat interface | Agent visualization
- Real-time agent reasoning display
- Tool call visualization
- Privacy tier selection
- Multi-scenario demos
- Perfect for 3-minute presentation!

Run with: streamlit run streamlit_demo.py
"""

import streamlit as st
import asyncio
from datetime import datetime
from typing import List, Dict, Any
import time

# LangChain imports
from langchain_core.messages import HumanMessage, AIMessage

# Our components
from workflows.crisis_to_resource import create_crisis_resource_workflow
from agents.base_agent import AgentState
from models.mock_data import therapist_db

# Page configuration
st.set_page_config(
    page_title="MindBridge AI Demo",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    /* Main container */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    /* Chat messages */
    .user-message {
        background: #4CAF50;
        color: white;
        padding: 12px 16px;
        border-radius: 12px;
        margin: 8px 0;
        max-width: 80%;
        float: right;
        clear: both;
    }

    .ai-message {
        background: #2196F3;
        color: white;
        padding: 12px 16px;
        border-radius: 12px;
        margin: 8px 0;
        max-width: 80%;
        float: left;
        clear: both;
    }

    /* Agent status */
    .agent-active {
        background: #FF9800;
        color: white;
        padding: 8px 12px;
        border-radius: 8px;
        font-weight: bold;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }

    /* Tool calls */
    .tool-call {
        background: #e3f2fd;
        border-left: 4px solid #2196F3;
        padding: 10px;
        margin: 8px 0;
        border-radius: 4px;
        font-family: monospace;
    }

    /* Risk levels */
    .risk-none { color: #4CAF50; font-weight: bold; }
    .risk-low { color: #8BC34A; font-weight: bold; }
    .risk-moderate { color: #FF9800; font-weight: bold; }
    .risk-high { color: #F44336; font-weight: bold; }
    .risk-immediate { color: #D32F2F; font-weight: bold; animation: blink 1s infinite; }

    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'workflow_state' not in st.session_state:
    st.session_state.workflow_state = None
if 'agent_logs' not in st.session_state:
    st.session_state.agent_logs = []
if 'current_agent' not in st.session_state:
    st.session_state.current_agent = None


def add_agent_log(agent: str, action: str, details: str = ""):
    """Add entry to agent reasoning log."""
    st.session_state.agent_logs.append({
        'timestamp': datetime.now().strftime("%H:%M:%S"),
        'agent': agent,
        'action': action,
        'details': details
    })


def display_agent_logs():
    """Display agent reasoning in real-time."""
    st.markdown("### 🧠 Agent Reasoning (Live)")

    # Current active agent
    if st.session_state.current_agent:
        st.markdown(
            f'<div class="agent-active">🔄 {st.session_state.current_agent} is working...</div>',
            unsafe_allow_html=True
        )

    # Logs container
    log_container = st.container()

    with log_container:
        for log in reversed(st.session_state.agent_logs[-10:]):  # Show last 10
            timestamp = log['timestamp']
            agent = log['agent']
            action = log['action']
            details = log['details']

            # Agent icon
            agent_icon = {
                'Crisis Agent': '🚨',
                'Resource Agent': '🔍',
                'Coordinator': '🎯',
                'System': '⚙️'
            }.get(agent, '🤖')

            st.markdown(f"**{timestamp}** {agent_icon} **{agent}**")
            st.markdown(f"└─ {action}")
            if details:
                st.markdown(f"   ```\n   {details}\n   ```")
            st.markdown("---")


def display_database_stats():
    """Show current therapist database status."""
    st.markdown("### 📊 Therapist Database")

    stats = therapist_db.get_statistics()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Therapists", stats['total_therapists'])

    with col2:
        st.metric("Available", stats['available'], delta=None)

    with col3:
        st.metric("Full", stats['full'], delta=None, delta_color="inverse")

    # Progress bar for capacity
    if stats['total_therapists'] > 0:
        capacity_used = (stats['total_therapists'] - stats['available']) / stats['total_therapists']
        st.progress(capacity_used, text=f"Capacity: {int(capacity_used * 100)}%")


def display_workflow_state():
    """Display current workflow state."""
    if not st.session_state.workflow_state:
        st.info("No active workflow. Send a message to begin.")
        return

    st.markdown("### 📋 Workflow Status")

    state = st.session_state.workflow_state

    # Risk level
    risk_level = state.get('risk_level', 'unknown')
    risk_class = f"risk-{risk_level}"
    risk_emoji = {
        'none': '🟢',
        'low': '🟡',
        'moderate': '🟠',
        'high': '🔴',
        'immediate': '🚨'
    }.get(risk_level, '❓')

    st.markdown(f"{risk_emoji} **Risk Level:** <span class='{risk_class}'>{risk_level.upper()}</span>", unsafe_allow_html=True)

    # Crisis detected
    crisis_detected = state.get('crisis_detected', False)
    st.markdown(f"🚨 **Crisis Detected:** {'✅ Yes' if crisis_detected else '❌ No'}")

    # Therapist match
    therapist_matched = state.get('therapist_matched', False)
    if therapist_matched:
        therapist_name = state.get('matched_therapist_name', 'Unknown')
        st.markdown(f"👨‍⚕️ **Matched Therapist:** {therapist_name}")
    else:
        st.markdown("👨‍⚕️ **Matched Therapist:** Not yet matched")

    # Workflow complete
    workflow_complete = state.get('workflow_complete', False)
    if workflow_complete:
        st.success("✅ Workflow Complete!")


async def process_message(user_message: str, privacy_tier: str):
    """Process user message through workflow."""
    # Add user message to chat
    st.session_state.messages.append({
        'role': 'user',
        'content': user_message,
        'timestamp': datetime.now()
    })

    # Log start
    add_agent_log('System', 'New message received', user_message[:100])
    st.session_state.current_agent = 'Coordinator'

    # Create workflow
    add_agent_log('Coordinator', 'Creating multi-agent workflow')
    workflow = create_crisis_resource_workflow()

    # Initialize state
    from langchain_core.messages import HumanMessage

    initial_state = {
        'messages': [HumanMessage(content=user_message)],
        'user_id': 'demo_user',
        'privacy_tier': privacy_tier,
        'risk_level': None,
        'crisis_detected': False,
        'therapist_matched': False,
        'matched_therapist_id': None,
        'matched_therapist_name': None,
        'next_step': None,
        'workflow_complete': False
    }

    # Run workflow with step tracking
    add_agent_log('Coordinator', 'Starting Crisis Agent')
    st.session_state.current_agent = 'Crisis Agent'

    # Execute workflow
    final_state = await workflow.ainvoke(initial_state)

    # Update session state
    st.session_state.workflow_state = final_state
    st.session_state.current_agent = None

    # Extract AI response
    if final_state['messages']:
        ai_response = final_state['messages'][-1].content
        st.session_state.messages.append({
            'role': 'assistant',
            'content': ai_response,
            'timestamp': datetime.now()
        })

    add_agent_log('System', 'Workflow complete', f"Risk: {final_state.get('risk_level')}")


def main():
    """Main Streamlit app."""

    # Header
    st.title("🧠 MindBridge AI - Agentic Mental Health Support")
    st.markdown("*Powered by NVIDIA Nemotron • Multi-Agent LangGraph Orchestration*")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Demo Controls")

        # Privacy tier selection
        st.markdown("### 🔒 Privacy Tier")
        privacy_tier = st.selectbox(
            "Select privacy level:",
            ["full_support", "assisted_handoff", "your_private_notes", "no_records"],
            help="Controls how much AI assistance is provided"
        )

        # Pre-loaded scenarios
        st.markdown("### 📝 Quick Scenarios")

        if st.button("🚨 High-Risk Crisis", use_container_width=True):
            scenario_message = "I feel completely hopeless. I don't think I can go on anymore. Everything hurts."
            asyncio.run(process_message(scenario_message, privacy_tier))
            st.rerun()

        if st.button("😰 Moderate Anxiety", use_container_width=True):
            scenario_message = "I've been having panic attacks and can't sleep. I really need help."
            asyncio.run(process_message(scenario_message, privacy_tier))
            st.rerun()

        if st.button("😊 General Support", use_container_width=True):
            scenario_message = "I'm feeling a bit stressed about work. Just need someone to talk to."
            asyncio.run(process_message(scenario_message, privacy_tier))
            st.rerun()

        # Clear button
        if st.button("🔄 Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.workflow_state = None
            st.session_state.agent_logs = []
            st.session_state.current_agent = None
            st.rerun()

        st.markdown("---")

        # Database stats
        display_database_stats()

    # Main content: Split screen
    col_chat, col_reasoning = st.columns([1, 1])

    # LEFT: Chat Interface
    with col_chat:
        st.markdown("### 💬 Chat Interface")

        # Chat history
        chat_container = st.container(height=400)
        with chat_container:
            for msg in st.session_state.messages:
                role = msg['role']
                content = msg['content']

                if role == 'user':
                    st.markdown(f'<div class="user-message">👤 {content}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="ai-message">🤖 {content}</div>', unsafe_allow_html=True)

        # Input
        user_input = st.text_input(
            "Your message:",
            placeholder="How are you feeling today?",
            key="user_input"
        )

        if st.button("Send", use_container_width=True) and user_input:
            with st.spinner("Processing..."):
                asyncio.run(process_message(user_input, privacy_tier))
            st.rerun()

    # RIGHT: Agent Reasoning
    with col_reasoning:
        # Workflow state
        display_workflow_state()

        st.markdown("---")

        # Agent logs
        display_agent_logs()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p><strong>MindBridge AI</strong> - NVIDIA Nemotron Hackathon 2024</p>
        <p>Demonstrating TRUE agentic AI with autonomous decision-making</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
