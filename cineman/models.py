"""
Database models for CineMan movie interactions.

This module defines SQLAlchemy models for storing user interactions with movies:
- MovieInteraction: Stores likes, dislikes, and watchlist status
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class MovieInteraction(db.Model):
    """
    Stores user interactions with movies in a session-based manner.
    Each record represents a user's interaction with a specific movie.
    """
    __tablename__ = 'movie_interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), nullable=False, index=True)
    movie_title = db.Column(db.String(255), nullable=False)
    movie_year = db.Column(db.String(10), nullable=True)
    movie_poster_url = db.Column(db.String(512), nullable=True)
    director = db.Column(db.String(255), nullable=True)
    imdb_rating = db.Column(db.String(10), nullable=True)
    
    # Interaction flags
    liked = db.Column(db.Boolean, default=False, nullable=False)
    disliked = db.Column(db.Boolean, default=False, nullable=False)
    in_watchlist = db.Column(db.Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Create a unique constraint on session_id and movie_title
    __table_args__ = (
        db.UniqueConstraint('session_id', 'movie_title', name='uq_session_movie'),
    )
    
    def to_dict(self):
        """Convert the interaction to a dictionary for JSON serialization."""
        return {
            'id': self.id,
            'movie_title': self.movie_title,
            'movie_year': self.movie_year,
            'movie_poster_url': self.movie_poster_url,
            'director': self.director,
            'imdb_rating': self.imdb_rating,
            'liked': self.liked,
            'disliked': self.disliked,
            'in_watchlist': self.in_watchlist,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f'<MovieInteraction {self.movie_title} ({self.session_id})>'
