
import pytest
import os
import sys
from cineman.app import app
from cineman.models import db
from cineman.cache import get_cache, reset_global_cache

@pytest.fixture(autouse=True)
def clean_env():
    """Ensure clean environment state for every test."""
    # Reset cache before and after test
    reset_global_cache()
    
    yield
    
    reset_global_cache()

@pytest.fixture(scope='function')
def test_app():
    """Create a fresh Flask app context for each test."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture(autouse=True)
def clear_cache_content():
    """Clear cache content automatically for every test."""
    cache = get_cache()
    if cache:
        cache.clear()
