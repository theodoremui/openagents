#############################################################################
# Home.py
#
# Main Streamlit application for agent testing and evaluation.
#
# This module provides:
# - Main entry point for the Streamlit frontend_stream (Home page)
# - Navigation and routing
# - Modern UI styling
#
#############################################################################

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure page (must be first Streamlit command)
st.set_page_config(
    page_title="Open Agent Evaluation Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Set sidebar title at the top (immediately after page config)
st.sidebar.markdown("# Open Agent")

# Load custom CSS for modern UI
from frontend_stream.utils.css_loader import load_css
load_css("static/css/styles.css")

# Initialize session state
if 'agents_loaded' not in st.session_state:
    st.session_state.agents_loaded = False
if 'current_agent' not in st.session_state:
    st.session_state.current_agent = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = {}


# Main landing page
st.title("🤖 Open Agent Evaluation Platform")
st.markdown("---")

st.markdown("""
Welcome to the Agent Testing & Evaluation Platform!

This platform provides a comprehensive interface for testing and evaluating different types of AI agents.

### Quick Start

1. **Agent Testing** - Test agents with interactive chat interface
2. **Configuration** - Manage agent configurations and settings
3. **About** - Learn more about the platform

### Features

- 🧪 **Interactive Testing** - Chat with agents in real-time
- ⚙️ **Configuration Management** - Edit agent settings via YAML
- 📊 **Multiple Agent Types** - Support for geo, finance, yelp, and general agents
- 🎨 **Modern UI** - Clean, responsive interface

Use the navigation sidebar or the top navigation bar to explore different sections.
""")

# Display available agents
try:
    from asdrp.agents.config_loader import AgentConfigLoader
    
    config_path = project_root / "config" / "open_agents.yaml"
    config_loader = AgentConfigLoader(config_path=str(config_path))
    available_agents = config_loader.list_agents()
    
    if available_agents:
        st.markdown("### Available Agents")
        cols = st.columns(min(len(available_agents), 4))
        
        for idx, agent_name in enumerate(available_agents):
            with cols[idx % len(cols)]:
                agent_config = config_loader.get_agent_config(agent_name)
                st.info(f"**{agent_config.display_name}**\n\n{agent_config.module}")

except Exception as e:
    st.warning(f"Could not load agent configuration: {str(e)}")

st.markdown("---")
st.markdown("*Use the navigation menu above to get started.*")

