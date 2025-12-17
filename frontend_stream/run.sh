#!/bin/bash
# Run script for the Streamlit frontend_stream with HTML wrapper

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Open Agent - Starting Application"
echo "=========================================="
echo ""
echo "Step 1: Starting Streamlit server on port 8501..."
echo ""

# Start Streamlit in background
streamlit run frontend_stream/Home.py --server.port 8501 --server.headless true &
STREAMLIT_PID=$!
echo "Streamlit started with PID: $STREAMLIT_PID"
echo ""

# Wait for Streamlit to be ready
echo "Waiting for Streamlit to start..."
sleep 5

# Check if Streamlit is running
if curl -s http://localhost:8501 > /dev/null 2>&1; then
    echo "✓ Streamlit is running on http://localhost:8501"
else
    echo "⚠ Warning: Streamlit may not be ready yet"
fi

echo ""
echo "Step 2: Starting HTML wrapper server on port 8080..."
echo ""

# Start simple HTTP server for HTML wrapper in background
# Python's http.server automatically serves index.html at root "/"
cd "$SCRIPT_DIR"
python3 -m http.server 8080 &
HTTP_SERVER_PID=$!

# Wait a moment for HTTP server to start
sleep 2

echo "=========================================="
echo "Application is ready!"
echo "=========================================="
echo ""
echo "Opening browser to: http://localhost:8080/#Home"
echo ""

# Open browser automatically
if command -v open > /dev/null; then
    # macOS
    open "http://localhost:8080/#Home"
elif command -v xdg-open > /dev/null; then
    # Linux
    xdg-open "http://localhost:8080/#Home"
elif command -v start > /dev/null; then
    # Windows
    start "http://localhost:8080/#Home"
else
    echo "Please open http://localhost:8080/#Home in your browser"
fi

echo "Press Ctrl+C to stop both servers"
echo ""

# Trap Ctrl+C to kill both servers
trap "echo ''; echo 'Stopping servers...'; kill $STREAMLIT_PID $HTTP_SERVER_PID 2>/dev/null; exit" INT TERM

# Keep script running and wait for HTTP server
wait $HTTP_SERVER_PID

