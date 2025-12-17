#############################################################################
# about.py
#
# About page with information about the application.
#
#############################################################################

import streamlit as st

def render_about():
    """Render the about page."""
    st.title("📖 About")
    
    st.markdown("""
    ## Agent Testing & Evaluation Platform
    
    This platform provides a comprehensive interface for testing and evaluating
    different types of AI agents.
    
    ### Features
    
    - **Agent Testing**: Interactive chat interface for testing agents
    - **Configuration Management**: Edit and manage agent configurations
    - **Multiple Agent Types**: Support for various agent implementations
    - **Real-time Evaluation**: Test agents with custom prompts and configurations
    
    ### Available Agent Types
    
    - **GeoAgent**: Geocoding and reverse geocoding
    - **FinanceAgent**: Financial data and market information
    - **YelpAgent**: Business and restaurant search
    - **OneAgent**: General-purpose agent with web search
    
    ### Architecture
    
    The platform uses:
    - **Streamlit** for the frontend_stream interface
    - **Agent Factory Pattern** for agent creation
    - **YAML Configuration** for agent settings
    - **Protocol-based Design** for agent interfaces
    
    ### Getting Started
    
    1. Navigate to **Agent Testing** to start testing agents
    2. Select an agent from the sidebar
    3. Configure the agent settings (model, temperature, instructions)
    4. Click **Load Agent** to initialize
    5. Start chatting with the agent!
    
    ### Configuration
    
    Agent configurations are stored in `config/open_agents.yaml`. You can:
    - Edit configurations directly in the **Configuration** page
    - Modify agent settings (model, temperature, instructions)
    - Enable/disable agents
    - Add new agent types
    
    ### Development
    
    This platform is designed to be extensible. New agent types can be added by:
    1. Creating a new agent implementation following the `AgentProtocol`
    2. Adding the agent configuration to `config/open_agents.yaml`
    3. The agent will automatically appear in the interface
    """)
    
    st.markdown("---")
    st.markdown("**Version:** 1.0.0")
    st.markdown("**Built with:** Streamlit, Python, OpenAI Agents")

