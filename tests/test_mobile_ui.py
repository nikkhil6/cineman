"""
Tests for mobile UI rendering and styling.

This module tests that the mobile UI fixes are properly applied in the HTML/CSS.
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import cineman
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.app import app


class TestMobileUI(unittest.TestCase):
    """Test cases for mobile UI functionality."""
    
    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()
    
    def test_index_page_loads(self):
        """Test that the index page loads successfully."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CineMan', response.data)
    
    def test_mobile_css_includes_flipped_card_fixes(self):
        """Test that mobile CSS includes proper flipped card styling."""
        response = self.client.get('/')
        html_content = response.data.decode('utf-8')
        
        # Check for mobile media query
        self.assertIn('@media (max-width:720px)', html_content)
        
        # Check for flipped card mobile fixes
        self.assertIn('.flip-card.is-flipped', html_content)
        
        # Check for important position fixes
        self.assertIn('position: fixed !important', html_content)
        
        # Check for mobile scrolling support
        self.assertIn('-webkit-overflow-scrolling: touch', html_content)
        
        # Check for sticky action buttons
        self.assertIn('position: sticky !important', html_content)
        self.assertIn('bottom: 0 !important', html_content)
    
    def test_mobile_css_includes_layout_changes(self):
        """Test that mobile CSS includes layout changes for better viewing."""
        response = self.client.get('/')
        html_content = response.data.decode('utf-8')
        
        # Check for column layout changes
        self.assertIn('flex-direction: column !important', html_content)
        
        # Check for max-height adjustments
        self.assertIn('max-height: 88vh', html_content)
        
        # Check for width adjustments
        self.assertIn('92vw', html_content)
    
    def test_movie_integration_js_loaded(self):
        """Test that movie integration JavaScript is loaded."""
        response = self.client.get('/')
        html_content = response.data.decode('utf-8')
        
        # Check that movie-integration.js is included
        self.assertIn('movie-integration.js', html_content)
    
    def test_responsive_poster_row_styling(self):
        """Test that poster row has responsive styling."""
        response = self.client.get('/')
        html_content = response.data.decode('utf-8')
        
        # Check for poster row mobile styles
        self.assertIn('.poster-row', html_content)
        
        # Check for horizontal scrolling on mobile
        self.assertIn('flex-wrap: nowrap', html_content)
        self.assertIn('overflow-x: auto', html_content)
        self.assertIn('scroll-snap-type', html_content)


class TestDesktopUI(unittest.TestCase):
    """Test cases for desktop UI functionality."""
    
    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()
    
    def test_desktop_flipped_card_styling(self):
        """Test that desktop flipped card styling is present."""
        response = self.client.get('/')
        html_content = response.data.decode('utf-8')
        
        # Check for desktop flipped card style
        self.assertIn('width: min(800px, 90vw)', html_content)
        self.assertIn('max-height: 85vh', html_content)
        
        # Check for backdrop blur
        self.assertIn('backdrop-filter: blur(4px)', html_content)
        self.assertIn('.poster-row.has-flipped-card::after', html_content)
    
    def test_action_buttons_styling(self):
        """Test that action buttons have proper styling."""
        response = self.client.get('/')
        html_content = response.data.decode('utf-8')
        
        # Check for action button classes
        self.assertIn('.action-buttons', html_content)
        self.assertIn('.like-btn', html_content)
        self.assertIn('.dislike-btn', html_content)
        self.assertIn('.watchlist-btn', html_content)
        
        # Check for active states
        self.assertIn('.like-btn.active', html_content)
        self.assertIn('.dislike-btn.active', html_content)
        self.assertIn('.watchlist-btn.active', html_content)


if __name__ == '__main__':
    unittest.main()
