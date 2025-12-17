#!/bin/bash
##############################################################################
# Real-Time Voice Agent Worker - Run Script
#
# This script handles setup and running of the LiveKit voice agent worker.
# The worker connects to LiveKit server and dispatches voice agents for
# incoming real-time voice sessions.
#
# Usage:
#   ./scripts/run_realtime.sh              # Run worker with defaults
#   ./scripts/run_realtime.sh --dev        # Run in development mode (verbose logging)
#   ./scripts/run_realtime.sh --test       # Run tests (worker + integration)
#   ./scripts/run_realtime.sh --install    # Install dependencies
#   ./scripts/run_realtime.sh --check      # Check configuration and connectivity
#   ./scripts/run_realtime.sh --help       # Show help
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_DIR="$PROJECT_ROOT/server"
CONFIG_FILE="$PROJECT_ROOT/config/voice_config.yaml"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

# Functions
print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  Real-Time Voice Agent Worker${NC}"
    echo -e "${CYAN}  LiveKit Agents Framework${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3.11 or higher."
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    print_success "Python $PYTHON_VERSION found"
}

get_python_exe() {
    # Prefer virtual environment Python if available (for uv-installed packages)
    if [ -f "$PROJECT_ROOT/.venv/bin/python3" ]; then
        echo "$PROJECT_ROOT/.venv/bin/python3"
    else
        # Fallback to system python3
        echo "python3"
    fi
}

check_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "Voice configuration file not found: $CONFIG_FILE"
        print_info "Please ensure config/voice_config.yaml exists"
        exit 1
    fi

    # Check for realtime section in config
    if ! grep -q "realtime:" "$CONFIG_FILE"; then
        print_warning "No 'realtime' section found in voice_config.yaml"
        print_info "Worker will use default real-time configuration"
    else
        print_success "Voice configuration file found with realtime section"
    fi
}

check_env() {
    if [ ! -f "$ENV_FILE" ]; then
        print_warning "Environment file (.env) not found"
        if [ -f "$ENV_EXAMPLE" ]; then
            print_info "Copying .env.example to .env..."
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            print_warning "Please edit .env and configure your API keys"
        else
            print_error ".env.example not found. Cannot create .env"
            exit 1
        fi
        return 1
    else
        print_success "Environment file found"
    fi

    # Load environment
    if [ -f "$ENV_FILE" ]; then
        export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)
    fi

    # Check required LiveKit variables
    local missing=0

    if [ -z "$LIVEKIT_URL" ]; then
        print_error "LIVEKIT_URL not set in .env"
        missing=1
    else
        print_success "LIVEKIT_URL configured"
    fi

    if [ -z "$LIVEKIT_API_KEY" ]; then
        print_error "LIVEKIT_API_KEY not set in .env"
        missing=1
    else
        print_success "LIVEKIT_API_KEY configured"
    fi

    if [ -z "$LIVEKIT_API_SECRET" ]; then
        print_error "LIVEKIT_API_SECRET not set in .env"
        missing=1
    else
        print_success "LIVEKIT_API_SECRET configured"
    fi

    if [ -z "$OPENAI_API_KEY" ]; then
        print_warning "OPENAI_API_KEY not set (required for STT/LLM/TTS)"
        missing=1
    else
        print_success "OPENAI_API_KEY configured"
    fi

    if [ $missing -eq 1 ]; then
        echo ""
        print_error "Missing required environment variables"
        print_info "Please edit .env and configure:"
        echo "  - LIVEKIT_URL (wss://your-project.livekit.cloud)"
        echo "  - LIVEKIT_API_KEY (from LiveKit dashboard)"
        echo "  - LIVEKIT_API_SECRET (from LiveKit dashboard)"
        echo "  - OPENAI_API_KEY (for voice AI)"
        echo ""
        print_info "Get LiveKit credentials from: https://cloud.livekit.io"
        exit 1
    fi

    return 0
}

install_dependencies() {
    print_header
    echo "Installing dependencies..."
    echo ""

    check_python

    cd "$PROJECT_ROOT"

    print_info "Installing OpenAgents with LiveKit dependencies..."
    python3 -m pip install -e .

    print_success "Dependencies installed"
    echo ""
    print_info "Required packages installed:"
    echo "  - livekit, livekit-agents, livekit-api"
    echo "  - livekit-plugins-openai, livekit-plugins-silero"
    echo "  - loguru (structured logging)"
}

check_connectivity() {
    print_header
    echo "Checking LiveKit connectivity..."
    echo ""

    check_python
    check_config
    if ! check_env; then
        return 1
    fi

    PYTHON_EXE=$(get_python_exe)
    cd "$PROJECT_ROOT"

    print_info "Testing LiveKit connection..."

    # Try to import and test configuration
    if "$PYTHON_EXE" -c "
import sys
import os
sys.path.insert(0, '$PROJECT_ROOT')
from server.voice.realtime.config import RealtimeVoiceConfig
try:
    config = RealtimeVoiceConfig.load()
    print('✓ Configuration loaded successfully')
    print(f'  LiveKit URL: {config.livekit_url}')
    print(f'  STT Model: {config.stt_model}')
    print(f'  TTS Voice: {config.tts_voice}')
    print(f'  Agent Type: {config.agent_type.value}')
except Exception as e:
    print(f'✗ Configuration error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1; then
        echo ""
        print_success "Configuration valid"
    else
        echo ""
        print_error "Configuration check failed"
        return 1
    fi

    echo ""
    print_info "Testing LiveKit server connectivity..."

    if "$PYTHON_EXE" -c "
import sys
import asyncio
sys.path.insert(0, '$PROJECT_ROOT')
from server.voice.realtime.service import RealtimeVoiceService
async def test():
    try:
        service = RealtimeVoiceService()
        health = await service.health_check()
        if health['livekit_connected']:
            print('✓ LiveKit server is reachable')
            print(f'  Status: {health[\"status\"]}')
            print(f'  Active rooms: {health.get(\"active_rooms\", 0)}')
            return True
        else:
            print(f'✗ LiveKit server not reachable: {health.get(\"error\")}', file=sys.stderr)
            return False
    except Exception as e:
        print(f'✗ Connection test failed: {e}', file=sys.stderr)
        return False

result = asyncio.run(test())
sys.exit(0 if result else 1)
" 2>&1; then
        echo ""
        print_success "All checks passed - ready to run worker"
        return 0
    else
        echo ""
        print_error "Connectivity check failed"
        print_info "Verify:"
        echo "  1. LiveKit server URL is correct (wss://...)"
        echo "  2. API credentials are valid"
        echo "  3. Network allows WebSocket connections"
        echo "  4. Firewall permits outbound connections to LiveKit"
        return 1
    fi
}

run_tests() {
    print_header
    echo "Running real-time voice tests..."
    echo ""

    check_python

    PYTHON_EXE=$(get_python_exe)
    cd "$PROJECT_ROOT"

    print_info "Running pytest for real-time voice module..."

    # Run tests if they exist
    if [ -d "tests/server/voice/realtime" ]; then
        "$PYTHON_EXE" -m pytest tests/server/voice/realtime/ -v --cov=server.voice.realtime --cov-report=term-missing
    else
        print_warning "No tests found in tests/server/voice/realtime/"
        print_info "Running basic import test..."

        "$PYTHON_EXE" -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from server.voice.realtime.config import RealtimeVoiceConfig
from server.voice.realtime.service import RealtimeVoiceService
from server.voice.realtime.agent import VoiceAgent
from server.voice.realtime.models import AgentType, VoiceState
print('✓ All imports successful')
"
        print_success "Import test passed"
    fi
}

run_worker() {
    local DEV_MODE=$1

    print_header

    # Pre-flight checks
    check_python
    check_config
    if ! check_env; then
        exit 1
    fi

    PYTHON_EXE=$(get_python_exe)

    # Set environment
    if [ -f "$ENV_FILE" ]; then
        export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)
    fi

    # Configure logging based on mode
    if [ "$DEV_MODE" = "true" ]; then
        export LOG_LEVEL=DEBUG
        print_info "Running in DEVELOPMENT mode (verbose logging)"
    else
        export LOG_LEVEL=${LOG_LEVEL:-INFO}
        print_info "Running in PRODUCTION mode"
    fi

    echo ""
    print_info "Worker configuration:"
    echo "  - LiveKit URL: ${LIVEKIT_URL}"
    echo "  - Python: $PYTHON_EXE"
    echo "  - Log Level: ${LOG_LEVEL}"
    echo "  - Config: $CONFIG_FILE"
    echo ""

    # Check if backend server is running
    print_info "Checking if backend server is running..."
    if curl -s -f "http://localhost:8000/health" > /dev/null 2>&1; then
        print_success "Backend server is running"
    else
        print_warning "Backend server not detected at http://localhost:8000"
        print_info "The worker can run independently, but you may want to start the backend:"
        echo "  ./scripts/run_server.sh --dev"
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Aborted. Start backend first with: ./scripts/run_server.sh --dev"
            exit 0
        fi
    fi

    cd "$PROJECT_ROOT"

    print_success "Starting LiveKit voice agent worker..."
    echo ""
    print_info "Worker will:"
    echo "  ✓ Connect to LiveKit server"
    echo "  ✓ Wait for voice session jobs"
    echo "  ✓ Dispatch agents to rooms"
    echo "  ✓ Handle STT → LLM → TTS pipeline"
    echo ""
    print_info "Press Ctrl+C to stop"
    echo ""

    # Run the worker with appropriate command
    if [ "$DEV_MODE" = "true" ]; then
        # LiveKit auto-reload is not supported on iTerm2; avoid a scary "[error]" message by disabling it.
        if [ "${TERM_PROGRAM}" = "iTerm.app" ]; then
            "$PYTHON_EXE" -m server.voice.realtime.worker dev --no-reload
        else
            "$PYTHON_EXE" -m server.voice.realtime.worker dev
        fi
    else
        "$PYTHON_EXE" -m server.voice.realtime.worker start
    fi
}

show_help() {
    print_header
    cat << EOF
Usage: ./scripts/run_realtime.sh [OPTION]

Options:
  --install       Install dependencies (LiveKit packages)
  --dev           Run worker in development mode (verbose logging)
  --test          Run tests for real-time voice module
  --check         Check configuration and LiveKit connectivity
  --download-models  Download turn detection model files (required for turn detection)
  --help          Show this help message

Examples:
  ./scripts/run_realtime.sh                    Run worker (production mode)
  ./scripts/run_realtime.sh --dev              Run with verbose logging
  ./scripts/run_realtime.sh --check            Test configuration and connectivity
  ./scripts/run_realtime.sh --download-models  Download turn detection model files
  ./scripts/run_realtime.sh --test             Run tests
  ./scripts/run_realtime.sh --install          Install dependencies

Prerequisites:
  1. Backend server should be running (./scripts/run_server.sh --dev)
  2. LiveKit credentials configured in .env:
     - LIVEKIT_URL (wss://your-project.livekit.cloud)
     - LIVEKIT_API_KEY
     - LIVEKIT_API_SECRET
  3. OpenAI API key configured:
     - OPENAI_API_KEY

Configuration:
  - Main config: config/voice_config.yaml (under 'realtime' section)
  - Environment: .env file in project root
  - Shared settings: STT/TTS inherit from voice.providers.openai

What This Worker Does:
  The real-time voice worker connects to LiveKit server and waits for
  voice session jobs. When a user creates a session (via backend API),
  the worker dispatches a voice agent to the LiveKit room.

  The agent handles:
  - Speech-to-Text (STT) using OpenAI Whisper
  - Language Model (LLM) using SmartRouter or SingleAgent
  - Text-to-Speech (TTS) using OpenAI TTS
  - Voice Activity Detection (VAD) using Silero
  - Turn detection for natural conversations
  - User interruptions

Architecture:
  1. User creates session → Backend API (POST /voice/realtime/session)
  2. Backend creates LiveKit room + generates token
  3. Worker receives job dispatch from LiveKit
  4. Worker creates VoiceAgent and starts STT-LLM-TTS pipeline
  5. User connects with token → Real-time conversation begins

Quick Start:
  1. Get LiveKit credentials from https://cloud.livekit.io (free tier)
  2. Add to .env:
     LIVEKIT_URL=wss://your-project.livekit.cloud
     LIVEKIT_API_KEY=APIxxx
     LIVEKIT_API_SECRET=xxx
     OPENAI_API_KEY=sk-...
  3. Start backend: ./scripts/run_server.sh --dev
  4. Start worker: ./scripts/run_realtime.sh --dev
  5. Create session: curl -X POST http://localhost:8000/voice/realtime/session

Troubleshooting:
  - Run --check to test configuration and connectivity
  - Check logs for detailed error messages
  - Verify LiveKit credentials are valid
  - Ensure OpenAI API key has sufficient quota
  - Check that config/voice_config.yaml has 'realtime' section

For more information, see:
  - server/voice/realtime/README.md
  - .kiro/specs/voice/REALTIME_VOICE_IMPLEMENTATION.md
  - https://docs.livekit.io/agents/build/

EOF
}

download_model_files() {
    print_header
    echo "Downloading turn detection model files..."
    echo ""
    
    check_python
    PYTHON_EXE=$(get_python_exe)
    cd "$PROJECT_ROOT"
    
    print_info "This will download model files from HuggingFace (~50MB)"
    print_info "Download location: ~/.cache/huggingface/hub/"
    echo ""
    
    if "$PYTHON_EXE" -m server.voice.realtime.worker download-files; then
        echo ""
        print_success "Model files downloaded successfully"
        print_info "Turn detection will now work when enabled in config"
    else
        echo ""
        print_error "Failed to download model files"
        exit 1
    fi
}

# Main script
case "${1}" in
    --install)
        install_dependencies
        ;;
    --test)
        run_tests
        ;;
    --check)
        check_connectivity
        ;;
    --download-models)
        download_model_files
        ;;
    --dev)
        run_worker true
        ;;
    --help|-h)
        show_help
        ;;
    "")
        # No args - run in production mode
        run_worker false
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
