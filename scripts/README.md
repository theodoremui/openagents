# OpenAgents Scripts

This directory contains utility scripts for development, testing, and deployment of the OpenAgents system.

## 📁 Available Scripts

### 1. `run_server.sh` - Backend Server Management

Comprehensive script for managing the FastAPI backend server.

**Usage:**
```bash
./scripts/run_server.sh [OPTION]
```

**Options:**
- `--install` - Install dependencies using uv (creates server/.venv)
- `--dev` - Run server in development mode (auto-reload, auth disabled)
- `--test` - Run all tests with coverage
- `--help` - Show help message

**Examples:**
```bash
# Install dependencies (first time setup)
./scripts/run_server.sh --install

# Run in development mode
./scripts/run_server.sh --dev

# Run production mode
./scripts/run_server.sh

# Run tests
./scripts/run_server.sh --test
```

**Features:**
- ✅ Automatic virtual environment setup (server/.venv)
- ✅ Environment validation (.env configuration)
- ✅ Configuration file checking
- ✅ Python version verification
- ✅ Colored output for easy reading
- ✅ Comprehensive error messages

### 2. `run_realtime.sh` - Real-Time Voice Worker Management

Comprehensive script for managing the LiveKit real-time voice agent worker.

**Usage:**
```bash
./scripts/run_realtime.sh [OPTION]
```

**Options:**
- `--install` - Install LiveKit dependencies
- `--dev` - Run worker in development mode (verbose logging)
- `--test` - Run real-time voice tests
- `--check` - Check configuration and LiveKit connectivity
- `--help` - Show help message

**Examples:**
```bash
# Check configuration and connectivity
./scripts/run_realtime.sh --check

# Run in development mode
./scripts/run_realtime.sh --dev

# Run in production mode
./scripts/run_realtime.sh
```

**Features:**
- ✅ LiveKit connectivity testing
- ✅ Configuration validation (voice_config.yaml)
- ✅ Environment variable checking
- ✅ Python version verification
- ✅ Health check with backend API
- ✅ Comprehensive error messages
- ✅ No virtual environment required (uses system python3)

**Prerequisites:**
1. LiveKit credentials from https://cloud.livekit.io
2. Environment variables in `.env`:
   ```bash
   LIVEKIT_URL=wss://your-project.livekit.cloud
   LIVEKIT_API_KEY=APIxxx
   LIVEKIT_API_SECRET=xxx
   OPENAI_API_KEY=sk-...
   ```
3. Backend server running (./scripts/run_server.sh --dev)

**Complete Setup:**
```bash
# Terminal 1: Start backend
./scripts/run_server.sh --dev

# Terminal 2: Start voice worker
./scripts/run_realtime.sh --dev
```

### 3. `check_map_tools.sh` - MapAgent Tool Verification

Diagnostic script to verify MapAgent has access to the `get_static_map_url` tool.

**Usage:**
```bash
./scripts/check_map_tools.sh
```

**Purpose:**
- Checks if backend server is running
- Fetches MapAgent tool list via API
- Verifies `get_static_map_url` presence
- Provides actionable feedback

**Example Output:**
```
╔════════════════════════════════════════════════════════════════════╗
║          MapAgent Tool Availability Diagnostic                     ║
╚════════════════════════════════════════════════════════════════════╝

1. Checking if backend server is running...
   ✅ Server is running at http://localhost:8000

2. Fetching MapAgent tools...
   Total tools: 8

3. Tool list:
     1  get_address_by_coordinates
     2  get_coordinates_by_address
     3  get_distance_matrix
     4  get_place_details
     5  get_static_map_url
     6  get_travel_time_distance
     7  places_autocomplete
     8  search_places_nearby

4. Checking for get_static_map_url...
   ✅ SUCCESS: get_static_map_url is AVAILABLE
```

**Environment Variables:**
- `API_URL` - Backend server URL (default: http://localhost:8000)
- `OPENAGENTS_API_KEY` - API key for authentication

---

## 🚀 Quick Start

### First Time Setup

```bash
# 1. Make scripts executable
chmod +x scripts/*.sh

# 2. Install backend dependencies
./scripts/run_server.sh --install

# 3. Configure environment
cp .env.example .env
# Edit .env: Set OPENAI_API_KEY, GOOGLE_API_KEY, etc.

# 4. Run server in development mode
./scripts/run_server.sh --dev
```

### Daily Development

```bash
# Start backend server
./scripts/run_server.sh --dev

# In another terminal: Verify MapAgent tools
./scripts/check_map_tools.sh
```

---

## 📝 Script Development Guidelines

When adding new scripts to this folder:

### 1. Naming Convention
- Use lowercase with underscores: `script_name.sh`
- Use descriptive names: `check_map_tools.sh` not `check.sh`
- Suffix with `.sh` for shell scripts

### 2. File Header
Include a header comment with:
```bash
#!/bin/bash
###############################################################################
# script_name.sh
#
# Brief description of what the script does
#
# Usage:
#   ./scripts/script_name.sh [OPTIONS]
#
# Requirements:
#   - List any requirements here
###############################################################################

set -e  # Exit on error
```

### 3. Path Handling
Always use project-relative paths:
```bash
# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get project root (parent of scripts folder)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
```

### 4. Error Handling
- Use `set -e` to exit on errors
- Provide clear error messages
- Use color coding for output:
```bash
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
```

### 5. Documentation
- Add script to this README
- Include usage examples
- Document environment variables
- Explain output format

### 6. Testing
Before committing a new script:
- [ ] Test with all supported options
- [ ] Test error cases
- [ ] Verify help message works
- [ ] Check cross-platform compatibility (if needed)
- [ ] Update this README

---

## 🛠️ Troubleshooting

### "Permission denied" Error

```bash
# Make scripts executable
chmod +x scripts/*.sh
```

### "Command not found" Error

Scripts must be run from the project root:
```bash
# ✅ Correct (from project root)
./scripts/run_server.sh --dev

# ❌ Wrong (from scripts folder)
cd scripts && ./run_server.sh --dev
```

### Script Can't Find Project Files

Scripts use relative paths from the project root. Always run from:
```bash
/Users/pmui/dev/halo/openagents/
```

---

## 📚 Related Documentation

- **Backend Setup**: See `server/README.md`
- **Complete Guide**: See `docs/IMPLEMENTATION_GUIDE.md`
- **Quick Start**: See `docs/COMPLETE_TUTORIAL.md`
- **MapAgent Troubleshooting**: See `docs/MAP_IMAGE_DISPLAY_GUIDE.md`

---

### 4. `run_tests.sh` - Comprehensive Test Runner

Runs all tests across the project (backend + frontend) with colored output.

**Usage:**
```bash
./scripts/run_tests.sh
```

**Features:**
- ✅ Runs frontend tests (Jest)
- ✅ Runs backend unit tests (pytest)
- ✅ Tool extraction tests
- ✅ Interactive map tests
- ✅ Colored output with test summary
- ✅ Exit code 0 if all tests pass, 1 if any fail

**Example Output:**
```
==================================
OpenAgents Comprehensive Test Suite
==================================

Running Frontend Tests...
✓ Frontend tests passed
Tests: 163 passed

Running Backend Unit Tests...
✓ Tool extraction tests
✓ Interactive map tests

==================================
Test Summary
==================================
Total tests: 171
Passed: 171
Failed: 0

✓ All tests passed!
```

---

## 🔄 Future Scripts (Planned)

Potential scripts to add:

- `setup_frontend.sh` - Frontend dependency installation and setup
- `deploy.sh` - Deployment automation
- `check_deps.sh` - Dependency version checker
- `backup_db.sh` - Database backup utility
- `generate_docs.sh` - Auto-generate API documentation

---

**Last Updated**: December 10, 2025
**Maintained By**: OpenAgents Development Team
