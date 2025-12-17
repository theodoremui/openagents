# Frontend_stream - Agent Testing & Evaluation Platform

A Streamlit-based frontend_stream for testing and evaluating AI agents.

## Features

- **Agent Testing**: Interactive chat interface for testing agents
- **Configuration Management**: Edit and manage agent configurations via YAML
- **Multiple Agent Types**: Support for various agent implementations
- **Real-time Evaluation**: Test agents with custom prompts and configurations
- **Modern UI**: Clean, responsive interface with navigation

## Running the Frontend_stream

### Prerequisites

- Python 3.13+
- All project dependencies installed (see main README)

### Start the Application

**Option 1: Using HTML wrapper with top navigation (Recommended)**
```bash
# From the project root
./frontend_stream/run.sh

# This will:
# 1. Start Streamlit on http://localhost:8501
# 2. Start HTML server on http://localhost:8080
# 3. Open http://localhost:8080/ in your browser
#    (index.html loads automatically and displays Home.py)
```

**Option 2: Direct Streamlit (traditional navigation)**
```bash
# From the project root
streamlit run frontend_stream/Home.py

# Or using uv
uv run streamlit run frontend_stream/Home.py
```

The HTML wrapper provides a custom top navigation bar, while direct Streamlit uses Streamlit's built-in navigation.

## Usage

### Agent Testing

1. Navigate to **Agent Testing** page
2. Select an agent from the sidebar
3. Configure agent settings:
   - Model name
   - Temperature (0.0-2.0)
   - Max tokens
   - System instructions
4. Click **Load Agent** to initialize
5. Start chatting with the agent!

### Configuration Management

1. Navigate to **Configuration** page
2. Choose from three views:
   - **YAML Editor**: Edit raw YAML configuration
   - **Agent Settings**: Configure individual agents via forms
   - **Visual Editor**: Coming soon
3. Save changes to update `config/open_agents.yaml`

## Architecture

```
frontend_stream/
├── Home.py                # Main Streamlit application (landing page)
├── pages/                 # Streamlit multi-page navigation
│   ├── 1_Agent_Testing.py    # Agent testing page
│   ├── 2_Configuration.py    # Configuration page
│   └── 3_About.py           # About page
├── modules/               # Page rendering modules
│   ├── agent_testing.py   # Agent testing logic
│   ├── configuration.py   # Configuration management logic
│   └── about.py           # About page logic
└── utils/                 # Utility functions
```

### Multi-Page Navigation

The app uses Streamlit's built-in multi-page navigation feature. Pages are automatically detected from the `pages/` directory:
- Files prefixed with numbers determine navigation order
- Underscores in filenames become spaces in the navigation menu
- Each page is a standalone Streamlit app that imports rendering logic from `modules/`

## Testing

Run frontend_stream tests:

```bash
pytest tests/frontend/
```

## Development

The frontend_stream uses:
- **Streamlit** for the UI framework
- **Agent Factory** for agent creation
- **YAML** for configuration management
- **Protocol-based Design** for agent interfaces

## Notes

- Agent configurations are stored in `config/open_agents.yaml`
- Changes to configuration are saved immediately
- Chat history is maintained per agent in session state
- Model settings can be adjusted at runtime

