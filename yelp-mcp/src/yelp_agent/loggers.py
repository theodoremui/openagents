"""
Logger setup for the fusion_ai module.

CRITICAL: For MCP stdio transport, ALL logging MUST go to stderr, NEVER stdout.
Per MCP spec: "Server MUST NOT write anything to stdout that isn't a valid MCP message"
"""
import logging
import sys
import os

# Get log level from environment variable (uppercase as per FastMCP requirement)
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)

# Configure logging to EXPLICITLY use stderr only
# This is CRITICAL for MCP stdio transport - stdout must remain clean for JSON-RPC messages
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(stream=sys.stderr),  # EXPLICITLY use stderr
    ],
    force=True,  # Override any existing configuration
)

logger = logging.getLogger("yelp_agent")

# Ensure all Python warnings also go to stderr
import warnings
warnings.filterwarnings("default")
logging.captureWarnings(True)
