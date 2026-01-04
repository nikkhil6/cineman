#!/usr/bin/env python3
"""
Main entry point for running the Cineman Flask application.
"""

import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from cineman.app import app, init_db

if __name__ == '__main__':
    # Initialize database tables on startup
    init_db()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

