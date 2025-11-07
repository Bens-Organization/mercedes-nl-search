"""Vercel serverless function entry point for FastAPI."""
import sys
from pathlib import Path

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import the FastAPI app
from app import app

# Export for Vercel
# Vercel expects the ASGI app to be available at module level
