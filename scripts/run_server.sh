#!/bin/bash
##############################################################################
# Multi-Agent Orchestration Server - Run Script
#
# This script handles setup and running of the FastAPI backend server.
#
# Usage:
#   ./scripts/run_server.sh              # Run with defaults
#   ./scripts/run_server.sh --dev        # Run in development mode (reload enabled)
#   ./scripts/run_server.sh --test       # Run tests
#   ./scripts/run_server.sh --install    # Install dependencies
#   ./scripts/run_server.sh --help       # Show help
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_DIR="$PROJECT_ROOT/server"
VENV_DIR="$SERVER_DIR/.venv"
CONFIG_FILE="$PROJECT_ROOT/config/open_agents.yaml"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

# Functions
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Multi-Agent Orchestration Server${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
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

check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "uv not found. Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    print_success "uv package manager found"
    return 0
}

setup_venv() {
    print_info "Setting up virtual environment in server/.venv..."
    
    check_uv
    cd "$SERVER_DIR"
    
    # Use uv sync to create and sync the virtual environment
    if uv sync; then
        print_success "Virtual environment ready"
        return 0
    else
        print_error "Failed to setup virtual environment"
        exit 1
    fi
}

get_python_exe() {
    # Return the Python executable from the venv
    # Check Unix-style venv first
    if [ -f "$VENV_DIR/bin/python" ]; then
        echo "$VENV_DIR/bin/python"
    # Check Windows-style venv
    elif [ -f "$VENV_DIR/Scripts/python.exe" ]; then
        echo "$VENV_DIR/Scripts/python.exe"
    else
        # Fallback: use uv run to get the Python executable
        cd "$SERVER_DIR"
        if command -v uv &> /dev/null && [ -f "$SERVER_DIR/pyproject.toml" ]; then
            # Use uv run to get the Python path from the project's venv
            UV_PYTHON=$(uv run python -c "import sys; print(sys.executable)" 2>/dev/null)
            if [ -n "$UV_PYTHON" ] && [ -f "$UV_PYTHON" ]; then
                echo "$UV_PYTHON"
            else
                print_warning "Could not find venv Python, falling back to system python3"
                echo "python3"
            fi
        else
            print_warning "Could not find venv, falling back to system python3"
            echo "python3"
        fi
    fi
}

check_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "Configuration file not found: $CONFIG_FILE"
        print_info "Please create config/open_agents.yaml"
        exit 1
    fi
    print_success "Configuration file found"
}

check_env() {
    if [ ! -f "$ENV_FILE" ]; then
        print_warning "Environment file (.env) not found"
        if [ -f "$ENV_EXAMPLE" ]; then
            print_info "Copying .env.example to .env..."
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            print_warning "Please edit .env and configure your API keys"
            print_info "For development, set AUTH_ENABLED=false"
        else
            print_error ".env.example not found. Cannot create .env"
            exit 1
        fi
    else
        print_success "Environment file found"
    fi
}

install_dependencies() {
    print_header
    echo "Installing dependencies..."
    echo ""

    check_python
    check_uv

    cd "$SERVER_DIR"
    
    print_info "Syncing dependencies with uv..."
    if uv sync; then
        print_success "Dependencies installed"
    else
        print_error "Failed to install dependencies"
        exit 1
    fi
}

run_tests() {
    print_header
    echo "Running tests..."
    echo ""

    check_python
    check_uv
    
    # Ensure venv is set up
    if [ ! -d "$VENV_DIR" ]; then
        setup_venv
    fi
    
    PYTHON_EXE=$(get_python_exe)
    cd "$PROJECT_ROOT"

    print_info "Running pytest with venv Python..."
    "$PYTHON_EXE" -m pytest tests/server/ -v --cov=server --cov-report=term-missing
}

run_server() {
    local DEV_MODE=$1
    local ORCHESTRATOR=$2

    print_header

    # Pre-flight checks
    check_python
    check_uv
    check_config
    check_env

    # Ensure venv is set up
    if [ ! -d "$VENV_DIR" ]; then
        print_warning "Virtual environment not found. Setting up..."
        setup_venv
    fi

    PYTHON_EXE=$(get_python_exe)

    # Set environment
    if [ -f "$ENV_FILE" ]; then
        export $(grep -v '^#' "$ENV_FILE" | xargs)
    fi

    # Default to disabled auth in dev mode
    if [ "$DEV_MODE" = "true" ]; then
        export AUTH_ENABLED=${AUTH_ENABLED:-false}
        export RELOAD=true
        export LOG_LEVEL=debug
        print_info "Running in DEVELOPMENT mode (auth disabled, auto-reload enabled)"
    else
        export AUTH_ENABLED=${AUTH_ENABLED:-true}
        export RELOAD=false
        print_info "Running in PRODUCTION mode"
    fi

    # Set orchestrator (default if not specified)
    ORCHESTRATOR=${ORCHESTRATOR:-default}
    export ORCHESTRATOR

    echo ""
    print_info "Server configuration:"
    echo "  - Host: ${HOST:-0.0.0.0}"
    echo "  - Port: ${PORT:-8000}"
    echo "  - Auth: ${AUTH_ENABLED}"
    echo "  - Reload: ${RELOAD}"
    echo "  - Log Level: ${LOG_LEVEL:-info}"
    echo "  - Orchestrator: ${ORCHESTRATOR}"
    echo "  - Python: $PYTHON_EXE"
    echo "  - Venv: $VENV_DIR"
    echo ""

    cd "$PROJECT_ROOT"

    print_success "Starting server..."
    echo ""

    # Pass orchestrator argument to server
    "$PYTHON_EXE" -m server.main --orchestrator "$ORCHESTRATOR"
}

show_help() {
    print_header
    cat << EOF
Usage: ./scripts/run_server.sh [OPTION] [ORCHESTRATOR]

Options:
  --install       Install dependencies using uv (creates server/.venv)
  --dev           Run server in development mode (auto-reload, auth disabled)
  --test          Run all tests with coverage
  --help          Show this help message

Orchestrators:
  default         Standard agent routing (default)
  smartrouter     LLM-based multi-agent orchestration with query decomposition
  moe             Mixture of Experts orchestration with parallel execution

Examples:
  ./scripts/run_server.sh                          Run server with default orchestrator
  ./scripts/run_server.sh --dev                    Run with auto-reload (default orchestrator)
  ./scripts/run_server.sh default                  Run with default orchestrator
  ./scripts/run_server.sh smartrouter              Run with SmartRouter orchestrator
  ./scripts/run_server.sh moe                      Run with MoE orchestrator
  ./scripts/run_server.sh --dev smartrouter        Run in dev mode with SmartRouter
  ./scripts/run_server.sh --dev moe                Run in dev mode with MoE
  ./scripts/run_server.sh --test                   Run tests
  ./scripts/run_server.sh --install                Install dependencies

Environment:
  - Uses virtual environment in server/.venv (created automatically)
  - Configuration is loaded from .env file in project root
  - If .env doesn't exist, it will be created from .env.example
  - ORCHESTRATOR env var can override default (CLI arg takes precedence)

SmartRouter:
  The SmartRouter is an advanced orchestrator that uses LLMs to:
  - Interpret complex queries and classify their complexity
  - Decompose queries into independent subqueries
  - Route subqueries to specialist agents based on capabilities
  - Execute subqueries concurrently with timeout handling
  - Synthesize multiple responses into coherent answers
  - Evaluate answer quality using an LLM judge

  Configuration: config/smartrouter.yaml

MoE (Mixture of Experts):
  The MoE Orchestrator uses a three-tier pipeline for expert routing:
  - Expert Selection: Choose relevant experts based on query capabilities
  - Parallel Execution: Execute selected experts concurrently
  - Result Mixing: Combine expert outputs with confidence weighting
  - Semantic Caching: Cache results for improved performance
  - Session Management: Support for multi-turn conversations

  Configuration: config/moe.yaml

Quick Start:
  1. ./scripts/run_server.sh --install              # Install dependencies (creates venv)
  2. Edit .env file                                 # Configure API keys
  3. ./scripts/run_server.sh --dev                  # Run in development mode
  4. Visit http://localhost:8000                    # View API docs

For more information, see:
  - server/README.md
  - docs/SERVER_QUICK_START.md
  - docs/IMPLEMENTATION_GUIDE.md
  - docs/moe/moe_orchestrator.md
  - config/smartrouter.yaml
  - config/moe.yaml

EOF
}

# Main script
case "${1}" in
    --install)
        install_dependencies
        ;;
    --test)
        run_tests
        ;;
    --dev)
        # Dev mode with optional orchestrator
        ORCHESTRATOR="${2:-default}"
        run_server true "$ORCHESTRATOR"
        ;;
    --help|-h)
        show_help
        ;;
    "")
        # No args - use default orchestrator
        run_server false "default"
        ;;
    default|smartrouter|moe)
        # Orchestrator specified directly
        run_server false "$1"
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
