#!/usr/bin/env python3
"""
Main entry point for running the Cineman Flask application.
"""

from cineman.app import app

if __name__ == '__main__':
    app.run(debug=True)

