#############################################################################
# server.py
#
# Simple HTTP server to serve the HTML wrapper and proxy to Streamlit.
#
# This server serves the index.html file and proxies requests to Streamlit.
#
#############################################################################

import http.server
import socketserver
import webbrowser
from pathlib import Path
import sys

PORT = 8080
STREAMLIT_URL = "http://localhost:8501"

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent.parent), **kwargs)
    
    def end_headers(self):
        # Add CORS headers for iframe
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        super().end_headers()

def run_server():
    """Run the HTTP server."""
    frontend_stream_dir = Path(__file__).parent.parent
    
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        print(f"Server running at http://localhost:{PORT}/")
        print(f"Serving files from: {frontend_stream_dir}")
        print(f"Streamlit should be running at: {STREAMLIT_URL}")
        print("\nOpen http://localhost:8080/index.html in your browser")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()

if __name__ == "__main__":
    run_server()

