#############################################################################
# test_navigation.py
#
# Tests for Streamlit navigation structure.
#
#############################################################################

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestNavigation:
    """Test navigation structure."""
    
    def test_pages_directory_exists(self):
        """Test that pages directory exists."""
        pages_dir = project_root / "frontend_stream" / "pages"
        assert pages_dir.exists()
        assert pages_dir.is_dir()
    
    def test_streamlit_pages_exist(self):
        """Test that Streamlit page files exist."""
        pages_dir = project_root / "frontend_stream" / "pages"
        
        expected_pages = [
            "1_Agent_Testing.py",
            "2_Configuration.py",
            "3_About.py"
        ]
        
        for page_file in expected_pages:
            page_path = pages_dir / page_file
            assert page_path.exists(), f"Page file {page_file} does not exist"
            assert page_path.is_file(), f"{page_file} is not a file"
    
    def test_modules_directory_exists(self):
        """Test that modules directory exists."""
        modules_dir = project_root / "frontend_stream" / "modules"
        assert modules_dir.exists()
        assert modules_dir.is_dir()
    
    def test_module_files_exist(self):
        """Test that module files exist."""
        modules_dir = project_root / "frontend_stream" / "modules"
        
        expected_modules = [
            "agent_testing.py",
            "configuration.py",
            "about.py"
        ]
        
        for module_file in expected_modules:
            module_path = modules_dir / module_file
            assert module_path.exists(), f"Module file {module_file} does not exist"
            assert module_path.is_file(), f"{module_file} is not a file"
    
    def test_page_imports(self):
        """Test that pages can be imported."""
        # Test that we can import the page modules
        from frontend_stream.modules.agent_testing import render_agent_testing
        from frontend_stream.modules.configuration import render_configuration
        from frontend_stream.modules.about import render_about
        
        assert callable(render_agent_testing)
        assert callable(render_configuration)
        assert callable(render_about)
    
    def test_streamlit_page_structure(self):
        """Test that Streamlit pages have correct structure."""
        pages_dir = project_root / "frontend_stream" / "pages"
        
        # Read agent testing page
        agent_page = pages_dir / "1_Agent_Testing.py"
        content = agent_page.read_text()
        
        # Check for required imports and structure
        assert "import streamlit as st" in content
        assert "from frontend_stream.modules.agent_testing import render_agent_testing" in content
        assert "st.set_page_config" in content
        assert "render_agent_testing()" in content

