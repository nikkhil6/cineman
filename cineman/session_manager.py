"""
Session Manager for CineMan application.
Handles chat history and recommended movies tracking per session.
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading


class SessionData:
    """Data structure to hold session information."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.chat_history: List[Dict[str, str]] = []
        self.recommended_movies: List[str] = []
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
    
    def add_message(self, role: str, content: str):
        """Add a message to chat history."""
        self.chat_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_accessed = datetime.now()
    
    def add_recommended_movies(self, movies: List[str]):
        """Add movies to the recommended list."""
        for movie in movies:
            if movie not in self.recommended_movies:
                self.recommended_movies.append(movie)
        self.last_accessed = datetime.now()
    
    def get_chat_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Get chat history, optionally limited to last N messages."""
        if limit:
            return self.chat_history[-limit:]
        return self.chat_history
    
    def get_recommended_movies(self) -> List[str]:
        """Get list of all recommended movies in this session."""
        return self.recommended_movies.copy()


class SessionManager:
    """Manages user sessions for the CineMan application."""
    
    def __init__(self, session_timeout_minutes: int = 60):
        self._sessions: Dict[str, SessionData] = {}
        self._lock = threading.Lock()
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
    
    def create_session(self) -> str:
        """Create a new session and return the session ID."""
        session_id = str(uuid.uuid4())
        with self._lock:
            self._sessions[session_id] = SessionData(session_id)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data by session ID."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                # Check if session has expired
                if datetime.now() - session.last_accessed > self.session_timeout:
                    del self._sessions[session_id]
                    return None
                session.last_accessed = datetime.now()
            return session
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> tuple[str, SessionData]:
        """Get existing session or create a new one."""
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session_id, session
        
        # Create new session if not found or expired
        new_session_id = self.create_session()
        return new_session_id, self._sessions[new_session_id]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        with self._lock:
            now = datetime.now()
            expired = [
                sid for sid, session in self._sessions.items()
                if now - session.last_accessed > self.session_timeout
            ]
            for sid in expired:
                del self._sessions[sid]
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        with self._lock:
            return len(self._sessions)


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(session_timeout_minutes=60)
    return _session_manager
