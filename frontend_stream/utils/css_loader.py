#############################################################################
# css_loader.py
#
# Utility function to load CSS files for Streamlit.
#
#############################################################################

import streamlit as st
from pathlib import Path


def load_css(css_file_path: str | Path) -> None:
    """
    Load and inject a CSS file into the Streamlit app.
    
    Args:
        css_file_path: Path to the CSS file (relative to frontend_stream directory or absolute)
    """
    css_path = Path(css_file_path)
    
    # If relative path, assume it's relative to frontend_stream directory
    if not css_path.is_absolute():
        frontend_stream_dir = Path(__file__).parent.parent
        css_path = frontend_stream_dir / css_path
    
    if not css_path.exists():
        st.warning(f"CSS file not found: {css_path}")
        return
    
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Failed to load CSS file: {str(e)}")

