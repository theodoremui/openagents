#!/bin/bash
# Run all tests including slow integration tests
# Use this before releases or when you need full test coverage

set -e

echo "=================================="
echo "Running ALL Tests (Including Slow)"
echo "=================================="
echo ""

# Run fast tests first
echo "Step 1: Running fast tests..."
echo "--------------------------------"
pytest tests/ -m "not slow" -v
FAST_EXIT_CODE=$?

if [ $FAST_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ Fast tests failed. Fix these before running slow tests."
    exit $FAST_EXIT_CODE
fi

echo ""
echo "✅ Fast tests passed!"
echo ""

# Run slow tests
echo "Step 2: Running slow integration tests..."
echo "--------------------------------"
echo "⚠️  This will make real API calls to OpenAI and Google Maps"
echo "⚠️  Estimated time: ~16 seconds"
echo ""

pytest tests/ -m "slow" -v
SLOW_EXIT_CODE=$?

if [ $SLOW_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ Slow tests failed."
    exit $SLOW_EXIT_CODE
fi

echo ""
echo "=================================="
echo "✅ All Tests Passed!"
echo "=================================="
echo ""
echo "Fast tests: ✅"
echo "Slow tests: ✅"
echo ""
echo "Full test coverage verified!"

