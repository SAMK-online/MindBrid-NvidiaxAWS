"""
Vercel Serverless Function Entry Point for FastAPI
===================================================

This file adapts our FastAPI app to work with Vercel's serverless model.
"""

import sys
import os

# Add parent directory to path so we can import voice_api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_api import app

# Vercel looks for an 'app' export
# Export the FastAPI app directly
app = app
