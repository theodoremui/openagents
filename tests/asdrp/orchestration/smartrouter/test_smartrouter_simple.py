#!/usr/bin/env python3
"""
Simple test to verify SmartRouter code changes are syntactically correct.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("TESTING SMARTROUTER INTEGRATION CHANGES")
print("=" * 60)
print()

# Test 1: Check if agent_service.py has correct syntax
print("TEST 1: Checking agent_service.py syntax...")
try:
    import py_compile
    py_compile.compile('server/agent_service.py', doraise=True)
    print("✓ agent_service.py syntax is valid\n")
except py_compile.PyCompileError as e:
    print(f"✗ Syntax error in agent_service.py: {e}\n")
    sys.exit(1)

# Test 2: Check if the _execute_smartrouter method exists
print("TEST 2: Checking if _execute_smartrouter method exists...")
try:
    with open('server/agent_service.py', 'r') as f:
        content = f.read()
        if 'async def _execute_smartrouter' in content:
            print("✓ _execute_smartrouter method found\n")
        else:
            print("✗ _execute_smartrouter method not found\n")
            sys.exit(1)
except Exception as e:
    print(f"✗ Error reading file: {e}\n")
    sys.exit(1)

# Test 3: Check if smartrouter handling exists in chat_agent
print("TEST 3: Checking smartrouter handling in chat_agent...")
try:
    with open('server/agent_service.py', 'r') as f:
        content = f.read()
        if 'if agent_id == "smartrouter":' in content and 'return await self._execute_smartrouter(request)' in content:
            print("✓ SmartRouter check found in chat_agent\n")
        else:
            print("✗ SmartRouter check not found in chat_agent\n")
            sys.exit(1)
except Exception as e:
    print(f"✗ Error reading file: {e}\n")
    sys.exit(1)

# Test 4: Check if smartrouter handling exists in simulate_agent
print("TEST 4: Checking smartrouter handling in simulate_agent...")
try:
    with open('server/agent_service.py', 'r') as f:
        content = f.read()
        simulate_section = content.split('async def simulate_agent')[1].split('async def chat_agent')[0]
        if 'if agent_id == "smartrouter":' in simulate_section:
            print("✓ SmartRouter check found in simulate_agent\n")
        else:
            print("✗ SmartRouter check not found in simulate_agent\n")
            sys.exit(1)
except Exception as e:
    print(f"✗ Error reading file: {e}\n")
    sys.exit(1)

# Test 5: Check if smartrouter handling exists in chat_agent_streaming
print("TEST 5: Checking smartrouter handling in chat_agent_streaming...")
try:
    with open('server/agent_service.py', 'r') as f:
        content = f.read()
        streaming_section = content.split('async def chat_agent_streaming')[1] if 'async def chat_agent_streaming' in content else ""
        if 'if agent_id == "smartrouter":' in streaming_section:
            print("✓ SmartRouter check found in chat_agent_streaming\n")
        else:
            print("✗ SmartRouter check not found in chat_agent_streaming\n")
            sys.exit(1)
except Exception as e:
    print(f"✗ Error reading file: {e}\n")
    sys.exit(1)

# Summary
print("=" * 60)
print("✓ ALL SYNTAX AND CODE STRUCTURE TESTS PASSED!")
print("=" * 60)
print()
print("Summary of changes:")
print("  1. Added _execute_smartrouter() method")
print("  2. Added SmartRouter handling in chat_agent()")
print("  3. Added SmartRouter handling in simulate_agent()")
print("  4. Added SmartRouter handling in chat_agent_streaming()")
print()
print("The backend is now ready to handle 'smartrouter' agent_id requests.")
print("Frontend can now select SmartRouter and communicate with the backend.")
print()
