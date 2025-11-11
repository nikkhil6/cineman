#!/usr/bin/env python3
"""
Main entry point for running the Cineman Flask application.
"""

from cineman.app import app, init_db

if __name__ == "__main__":
    # Initialize database tables on startup
    init_db()
    app.run(debug=True)
