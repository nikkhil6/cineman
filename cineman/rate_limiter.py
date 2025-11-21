"""
Rate Limiter for Gemini API Calls

Manages rate limiting for Gemini API calls with a daily limit.
Supports persistent storage via SQLite database to track API usage
across server restarts.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
from cineman.models import db
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.exc import OperationalError


class APIUsageTracker(db.Model):
    """Model to track API usage for rate limiting."""
    __tablename__ = 'api_usage_tracker'
    
    id = Column(Integer, primary_key=True)
    api_name = Column(String(50), unique=True, nullable=False)
    call_count = Column(Integer, default=0, nullable=False)
    reset_date = Column(DateTime, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'api_name': self.api_name,
            'call_count': self.call_count,
            'reset_date': self.reset_date.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }


class RateLimiter:
    """
    Rate limiter for API calls with daily limits.
    
    Attributes:
        api_name: Name of the API to track (e.g., 'gemini')
        daily_limit: Maximum number of API calls allowed per day
    """
    
    def __init__(self, api_name: str = "gemini", daily_limit: int = 50):
        """
        Initialize rate limiter.
        
        Args:
            api_name: Name of the API (default: 'gemini')
            daily_limit: Daily call limit (default: 50)
        """
        self.api_name = api_name
        self.daily_limit = daily_limit
    
    def _get_or_create_tracker(self) -> APIUsageTracker:
        """Get or create usage tracker record."""
        try:
            tracker = APIUsageTracker.query.filter_by(api_name=self.api_name).first()
            
            if not tracker:
                # Create new tracker with reset date set to tomorrow
                tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                tracker = APIUsageTracker(
                    api_name=self.api_name,
                    call_count=0,
                    reset_date=tomorrow
                )
                db.session.add(tracker)
                db.session.commit()
            
            return tracker
        except OperationalError:
            # If database is not available, return None
            # This allows the app to work without rate limiting in case of DB issues
            return None
    
    def _check_and_reset_if_needed(self, tracker: APIUsageTracker) -> None:
        """Check if counter needs to be reset and reset if necessary."""
        now = datetime.utcnow()
        
        # Reset counter if we've passed the reset date
        if now >= tracker.reset_date:
            tracker.call_count = 0
            # Set next reset to tomorrow at midnight UTC
            tracker.reset_date = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            tracker.last_updated = now
            db.session.commit()
    
    def check_limit(self) -> Tuple[bool, int, Optional[str]]:
        """
        Check if the rate limit has been exceeded.
        
        Returns:
            Tuple of (allowed, remaining_calls, error_message):
                - allowed: True if call is allowed, False if limit exceeded
                - remaining_calls: Number of calls remaining today
                - error_message: Error message if limit exceeded, None otherwise
        """
        try:
            tracker = self._get_or_create_tracker()
            
            if not tracker:
                # If tracker is not available, allow the call
                # This ensures the app works even if DB is down
                return (True, self.daily_limit, None)
            
            # Check if reset is needed
            self._check_and_reset_if_needed(tracker)
            
            # Check if limit exceeded
            if tracker.call_count >= self.daily_limit:
                remaining_calls = 0
                reset_time = tracker.reset_date.strftime('%Y-%m-%d %H:%M:%S UTC')
                error_msg = (
                    f"Daily API limit reached ({self.daily_limit} calls per day). "
                    f"Please try again after {reset_time}. "
                    f"The limit will reset at midnight UTC."
                )
                return (False, remaining_calls, error_msg)
            
            # Calculate remaining calls
            remaining_calls = self.daily_limit - tracker.call_count
            return (True, remaining_calls, None)
            
        except Exception as e:
            # Log the error but allow the call to proceed
            # This ensures the app continues working even if rate limiting fails
            print(f"Rate limiter error (allowing call): {e}")
            return (True, self.daily_limit, None)
    
    def increment(self) -> None:
        """Increment the API call counter."""
        try:
            tracker = self._get_or_create_tracker()
            
            if not tracker:
                return
            
            # Check if reset is needed before incrementing
            self._check_and_reset_if_needed(tracker)
            
            # Increment counter
            tracker.call_count += 1
            tracker.last_updated = datetime.utcnow()
            db.session.commit()
            
        except Exception as e:
            # Log the error but don't fail the request
            print(f"Rate limiter increment error: {e}")
            # Rollback any failed transaction
            try:
                db.session.rollback()
            except:
                pass
    
    def get_usage_stats(self) -> dict:
        """
        Get current usage statistics.
        
        Returns:
            Dictionary with usage stats including call_count, limit, remaining, and reset_date
        """
        try:
            tracker = self._get_or_create_tracker()
            
            if not tracker:
                return {
                    'call_count': 0,
                    'daily_limit': self.daily_limit,
                    'remaining': self.daily_limit,
                    'reset_date': None,
                    'status': 'unavailable'
                }
            
            # Check if reset is needed
            self._check_and_reset_if_needed(tracker)
            
            remaining = max(0, self.daily_limit - tracker.call_count)
            
            return {
                'call_count': tracker.call_count,
                'daily_limit': self.daily_limit,
                'remaining': remaining,
                'reset_date': tracker.reset_date.isoformat(),
                'status': 'active'
            }
            
        except Exception as e:
            print(f"Rate limiter stats error: {e}")
            return {
                'call_count': 0,
                'daily_limit': self.daily_limit,
                'remaining': self.daily_limit,
                'reset_date': None,
                'status': 'error'
            }
    
    def reset(self) -> None:
        """
        Manually reset the counter (for testing purposes).
        """
        try:
            tracker = self._get_or_create_tracker()
            
            if not tracker:
                return
            
            tracker.call_count = 0
            tracker.last_updated = datetime.utcnow()
            db.session.commit()
            
        except Exception as e:
            print(f"Rate limiter reset error: {e}")
            try:
                db.session.rollback()
            except:
                pass


# Global rate limiter instance for Gemini API
# Default: 50 calls per day (free tier limit)
gemini_rate_limiter = None


def get_gemini_rate_limiter() -> RateLimiter:
    """
    Get or create the global Gemini rate limiter instance.
    
    Returns:
        RateLimiter instance for Gemini API
    """
    global gemini_rate_limiter
    
    if gemini_rate_limiter is None:
        # Allow override via environment variable
        daily_limit = int(os.getenv('GEMINI_DAILY_LIMIT', '50'))
        gemini_rate_limiter = RateLimiter(api_name="gemini", daily_limit=daily_limit)
    
    return gemini_rate_limiter
