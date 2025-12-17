#############################################################################
# agent_testing.py
#
# Agent testing and evaluation page.
#
# This module provides:
# - Agent selection and configuration
# - Interactive chat interface
# - Agent execution and response display
#
#############################################################################

import streamlit as st
import asyncio
import importlib
from typing import Optional
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from asdrp.agents.agent_factory import AgentFactory
from asdrp.agents.config_loader import AgentConfigLoader
from agents import Runner

def render_agent_testing():
    """Render the agent testing page."""
    # Initialize session state variables
    if 'agents_loaded' not in st.session_state:
        st.session_state.agents_loaded = False
    if 'current_agent' not in st.session_state:
        st.session_state.current_agent = None
    if 'current_agent_name' not in st.session_state:
        st.session_state.current_agent_name = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = {}
    if 'last_selected_agent' not in st.session_state:
        st.session_state.last_selected_agent = None
    
    st.title("🤖 Agent Testing & Evaluation")
    st.markdown("Test and evaluate different agent types with interactive chat.")
    
    # Initialize factory and config loader
    config_path = project_root / "config" / "open_agents.yaml"
    factory = AgentFactory(config_path=str(config_path))
    config_loader = AgentConfigLoader(config_path=str(config_path))
    
    # Left sidebar for agent selection and configuration
    with st.sidebar:
        st.header("Agent Selection")
        
        # Get available agents
        try:
            available_agents = config_loader.list_agents()
            if not available_agents:
                st.error("No agents available. Please check configuration.")
                return
            
            # Agent selector
            selected_agent_name = st.selectbox(
                "Select Agent",
                available_agents,
                key="agent_selector"
            )
            
            if selected_agent_name:
                # Get agent config
                agent_config = config_loader.get_agent_config(selected_agent_name)
                
                st.markdown("---")
                st.subheader("Agent Configuration")
                
                # Display agent info
                st.info(f"**Name:** {agent_config.display_name}\n\n"
                       f"**Module:** {agent_config.module}\n\n"
                       f"**Enabled:** {'✅' if agent_config.enabled else '❌'}")
                
                # Model configuration
                st.markdown("#### Model Settings")
                model_name = st.text_input(
                    "Model Name",
                    value=agent_config.model.name,
                    key=f"model_name_{selected_agent_name}"
                )
                temperature = st.slider(
                    "Temperature",
                    min_value=0.0,
                    max_value=2.0,
                    value=float(agent_config.model.temperature),
                    step=0.1,
                    key=f"temperature_{selected_agent_name}"
                )
                max_tokens = st.number_input(
                    "Max Tokens",
                    min_value=100,
                    max_value=8000,
                    value=agent_config.model.max_tokens,
                    step=100,
                    key=f"max_tokens_{selected_agent_name}"
                )
                
                # Instructions editor
                st.markdown("#### Instructions")
                instructions = st.text_area(
                    "System Instructions",
                    value=agent_config.default_instructions,
                    height=150,
                    key=f"instructions_{selected_agent_name}"
                )
                
                # Automatically load agent when selection changes
                if st.session_state.last_selected_agent != selected_agent_name:
                    # Agent selection changed, automatically load it
                    load_agent(factory, selected_agent_name, instructions, model_name, temperature, max_tokens)
                    st.session_state.last_selected_agent = selected_agent_name
                
                # Manual reload button (optional, for reloading with updated settings)
                if st.button("🔄 Reload Agent", key=f"reload_{selected_agent_name}", use_container_width=True):
                    load_agent(factory, selected_agent_name, instructions, model_name, temperature, max_tokens)
                
                # Clear chat button
                if st.button("🗑️ Clear Chat", key=f"clear_{selected_agent_name}", use_container_width=True):
                    if 'chat_history' in st.session_state and selected_agent_name in st.session_state.chat_history:
                        st.session_state.chat_history[selected_agent_name] = []
                    st.rerun()
        
        except Exception as e:
            st.error(f"Error loading agents: {str(e)}")
            st.exception(e)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Chat Interface")
        
        if selected_agent_name:
            # Initialize chat history for this agent
            if selected_agent_name not in st.session_state.chat_history:
                st.session_state.chat_history[selected_agent_name] = []
            
            chat_history = st.session_state.chat_history[selected_agent_name]
            
            # Display chat history
            chat_container = st.container()
            with chat_container:
                for message in chat_history:
                    if message["role"] == "user":
                        with st.chat_message("user"):
                            st.write(message["content"])
                    elif message["role"] == "assistant":
                        with st.chat_message("assistant"):
                            st.write(message["content"])
                            if "error" in message:
                                st.error(f"Error: {message['error']}")
            
            # Chat input
            user_input = st.chat_input("Type your message here...")
            
            if user_input:
                # Add user message to history
                chat_history.append({"role": "user", "content": user_input})
                
                # Get current agent
                current_agent = st.session_state.get('current_agent')
                agent_name = st.session_state.get('current_agent_name')
                
                if current_agent and agent_name == selected_agent_name:
                    # Run agent
                    with st.spinner("Agent is thinking..."):
                        try:
                            response = asyncio.run(Runner.run(current_agent, input=user_input))
                            assistant_message = response.final_output if hasattr(response, 'final_output') else str(response)
                            
                            # Add assistant message to history
                            chat_history.append({
                                "role": "assistant",
                                "content": assistant_message
                            })
                        except Exception as e:
                            error_msg = str(e)
                            chat_history.append({
                                "role": "assistant",
                                "content": f"An error occurred while processing your request.",
                                "error": error_msg
                            })
                            st.error(f"Error: {error_msg}")
                            st.exception(e)
                    
                    st.rerun()
                else:
                    st.warning("Please load the agent first using the sidebar.")
                    chat_history.pop()  # Remove the user message if agent not loaded
    
    with col2:
        st.subheader("Agent Status")
        
        current_agent = st.session_state.get('current_agent')
        current_agent_name = st.session_state.get('current_agent_name')
        
        if current_agent:
            st.success(f"✅ {current_agent_name} loaded")
            st.info(f"**Name:** {current_agent.name}\n\n"
                   f"**Instructions:** {current_agent.instructions[:100]}...")
            
            # Statistics
            if 'chat_history' in st.session_state and selected_agent_name in st.session_state.chat_history:
                chat_count = len([m for m in st.session_state.chat_history[selected_agent_name] if m["role"] == "user"])
                st.metric("Messages Sent", chat_count)
        else:
            st.warning("No agent loaded")
            st.info("Select an agent and click 'Load Agent' to start testing.")


def load_agent(factory: AgentFactory, agent_name: str, instructions: str, 
               model_name: str, temperature: float, max_tokens: int):
    """Load an agent with the specified configuration."""
    try:
        from asdrp.agents.config_loader import ModelConfig
        
        # Create model config
        model_config = ModelConfig(
            name=model_name,
            temperature=temperature,
            max_tokens=int(max_tokens)
        )
        
        # Get the factory function directly to pass model_config
        # We need to create the agent with custom model config
        config_loader = AgentConfigLoader(config_path=str(project_root / "config" / "open_agents.yaml"))
        agent_config = config_loader.get_agent_config(agent_name)
        
        # Import the creation function
        module = importlib.import_module(agent_config.module)
        factory_func = getattr(module, agent_config.function)
        
        # Create agent with custom model config
        agent = factory_func(instructions=instructions, model_config=model_config)
        
        # Store in session state
        st.session_state.current_agent = agent
        st.session_state.current_agent_name = agent_name
        st.session_state.agents_loaded = True
        
        st.success(f"✅ {agent_name} loaded successfully!")
        
    except Exception as e:
        st.error(f"Failed to load agent: {str(e)}")
        st.exception(e)

