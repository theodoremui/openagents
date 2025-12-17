#############################################################################
# 1_Agent_Testing.py
#
# Streamlit page for agent testing and evaluation.
#
#############################################################################

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the page rendering function
from frontend_stream.modules.agent_testing import render_agent_testing

# Set page config (must be first Streamlit command)
st.set_page_config(
    page_title="Agent Testing",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS to hide sidebar navigation
from frontend_stream.utils.css_loader import load_css
load_css("static/css/styles.css")

# Render the page
render_agent_testing()

