#############################################################################
# configuration.py
#
# Configuration management page.
#
# This module provides:
# - YAML configuration editor
# - Agent configuration management
# - Save/load configuration
#
#############################################################################

import streamlit as st
import yaml
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from asdrp.agents.config_loader import AgentConfigLoader

def render_configuration():
    """Render the configuration management page."""
    st.title("⚙️ Configuration Management")
    st.markdown("Edit and manage agent configurations.")
    
    config_path = project_root / "config" / "open_agents.yaml"
    
    # Load current configuration
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
    except Exception as e:
        st.error(f"Failed to load configuration: {str(e)}")
        return
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["YAML Editor", "Agent Settings", "Visual Editor"])
    
    with tab1:
        st.subheader("YAML Configuration Editor")
        st.info("Edit the raw YAML configuration. Changes are saved immediately when you click 'Save Configuration'.")
        
        # YAML editor
        edited_config = st.text_area(
            "Configuration YAML",
            value=config_content,
            height=600,
            key="yaml_editor"
        )
        
        col1, col2, col3 = st.columns([1, 1, 4])
        
        with col1:
            if st.button("💾 Save", use_container_width=True):
                save_configuration(config_path, edited_config)
        
        with col2:
            if st.button("🔄 Reload", use_container_width=True):
                st.rerun()
        
        # Validate YAML
        if st.button("✅ Validate YAML", use_container_width=True):
            validate_yaml(edited_config)
    
    with tab2:
        st.subheader("Agent Settings")
        st.markdown("Configure individual agent settings.")
        
        try:
            config_loader = AgentConfigLoader(config_path=str(config_path))
            available_agents = config_loader.list_agents()
            
            if not available_agents:
                st.warning("No agents found in configuration.")
                return
            
            selected_agent = st.selectbox("Select Agent", available_agents)
            
            if selected_agent:
                agent_config = config_loader.get_agent_config(selected_agent)
                
                # Display current settings
                st.markdown("### Current Settings")
                
                with st.form(f"agent_form_{selected_agent}"):
                    display_name = st.text_input(
                        "Display Name",
                        value=agent_config.display_name
                    )
                    
                    enabled = st.checkbox(
                        "Enabled",
                        value=agent_config.enabled
                    )
                    
                    st.markdown("#### Model Configuration")
                    model_name = st.text_input(
                        "Model Name",
                        value=agent_config.model.name
                    )
                    temperature = st.slider(
                        "Temperature",
                        min_value=0.0,
                        max_value=2.0,
                        value=float(agent_config.model.temperature),
                        step=0.1
                    )
                    max_tokens = st.number_input(
                        "Max Tokens",
                        min_value=100,
                        max_value=8000,
                        value=agent_config.model.max_tokens,
                        step=100
                    )
                    
                    st.markdown("#### Instructions")
                    instructions = st.text_area(
                        "Default Instructions",
                        value=agent_config.default_instructions,
                        height=200
                    )
                    
                    submitted = st.form_submit_button("💾 Save Agent Configuration", use_container_width=True)
                    
                    if submitted:
                        update_agent_config(
                            config_path,
                            selected_agent,
                            display_name,
                            enabled,
                            model_name,
                            temperature,
                            max_tokens,
                            instructions
                        )
        
        except Exception as e:
            st.error(f"Error loading configuration: {str(e)}")
            st.exception(e)
    
    with tab3:
        st.subheader("Visual Configuration Editor")
        st.info("Coming soon: Visual editor for agent configurations.")


def save_configuration(config_path: Path, config_content: str):
    """Save configuration to file."""
    try:
        # Validate YAML first
        yaml.safe_load(config_content)
        
        # Save to file
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        st.success("✅ Configuration saved successfully!")
        st.balloons()
        return True
        
    except yaml.YAMLError as e:
        st.error(f"Invalid YAML: {str(e)}")
        return False
    except Exception as e:
        st.error(f"Failed to save configuration: {str(e)}")
        return False


def validate_yaml(yaml_content: str):
    """Validate YAML syntax."""
    try:
        data = yaml.safe_load(yaml_content)
        st.success("✅ YAML is valid!")
        
        # Check structure
        if 'agents' not in data:
            st.warning("⚠️ Missing 'agents' section")
        else:
            st.info(f"Found {len(data.get('agents', {}))} agent(s)")
        
        return True
    
    except yaml.YAMLError as e:
        st.error(f"❌ Invalid YAML: {str(e)}")
        return False


def update_agent_config(
    config_path: Path,
    agent_name: str,
    display_name: str,
    enabled: bool,
    model_name: str,
    temperature: float,
    max_tokens: int,
    instructions: str
):
    """Update agent configuration in YAML file."""
    try:
        # Load current config
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        if 'agents' not in config_data:
            st.error("Invalid configuration structure")
            return False
        
        if agent_name not in config_data['agents']:
            st.error(f"Agent '{agent_name}' not found")
            return False
        
        # Update agent config
        agent_config = config_data['agents'][agent_name]
        agent_config['display_name'] = display_name
        agent_config['enabled'] = enabled
        agent_config['default_instructions'] = instructions
        
        if 'model' not in agent_config:
            agent_config['model'] = {}
        
        agent_config['model']['name'] = model_name
        agent_config['model']['temperature'] = float(temperature)
        agent_config['model']['max_tokens'] = int(max_tokens)
        
        # Save updated config
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        st.success(f"✅ Configuration for '{agent_name}' updated successfully!")
        st.balloons()
        return True
        
    except Exception as e:
        st.error(f"Failed to update configuration: {str(e)}")
        st.exception(e)
        return False

