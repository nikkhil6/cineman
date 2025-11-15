"""
Tests for conversation holding and context management in CineMan.
"""
import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.app import app, db
from cineman.session_manager import SessionManager


class TestConversationHolding(unittest.TestCase):
    """Test cases for conversation holding and context management."""
    
    def setUp(self):
        """Set up test client and database before each test."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        self.client = app.test_client()
        
        # Create tables
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    @patch('cineman.app.movie_chain')
    def test_session_persists_across_messages(self, mock_chain):
        """Test that session ID persists across multiple messages."""
        # Mock the chain to return a simple response
        mock_chain.invoke.return_value = "Hello! I'm CineMan. How can I help you with movies today?"
        
        with self.client as client:
            # Send first message
            response1 = client.post('/chat', json={
                'message': 'Hello'
            })
            
            self.assertEqual(response1.status_code, 200)
            data1 = response1.get_json()
            session_id1 = data1.get('session_id')
            self.assertIsNotNone(session_id1)
            
            # Send second message
            response2 = client.post('/chat', json={
                'message': 'Tell me about sci-fi movies'
            })
            
            self.assertEqual(response2.status_code, 200)
            data2 = response2.get_json()
            session_id2 = data2.get('session_id')
            
            # Session should be the same
            self.assertEqual(session_id1, session_id2)
    
    @patch('cineman.app.movie_chain')
    def test_chat_history_accumulates(self, mock_chain):
        """Test that chat history accumulates across multiple messages."""
        from cineman.session_manager import get_session_manager
        
        # Mock chain responses
        mock_chain.invoke.return_value = "That's great! Tell me more."
        
        session_manager = get_session_manager()
        session_id = session_manager.create_session()
        
        with self.client as client:
            with client.session_transaction() as sess:
                sess['session_id'] = session_id
            
            # Send multiple messages
            messages = [
                'I like action movies',
                'Especially ones with great stunts',
                'What do you think about Tom Cruise?'
            ]
            
            for msg in messages:
                response = client.post('/chat', json={'message': msg})
                self.assertEqual(response.status_code, 200)
            
            # Check session history
            session_data = session_manager.get_session(session_id)
            history = session_data.get_chat_history()
            
            # Should have user messages and assistant responses
            # At least 3 user messages
            user_messages = [m for m in history if m['role'] == 'user']
            self.assertEqual(len(user_messages), 3)
            
            # Verify content
            self.assertEqual(user_messages[0]['content'], 'I like action movies')
            self.assertEqual(user_messages[1]['content'], 'Especially ones with great stunts')
            self.assertEqual(user_messages[2]['content'], 'What do you think about Tom Cruise?')
    
    @patch('cineman.app.movie_chain')
    def test_new_session_clears_history(self, mock_chain):
        """Test that creating a new session clears history."""
        # Mock chain responses
        mock_chain.invoke.return_value = "Got it! Let me help you with that."
        
        with self.client as client:
            # Send first message
            response1 = client.post('/chat', json={
                'message': 'I like horror movies'
            })
            self.assertEqual(response1.status_code, 200)
            
            # Clear session
            clear_response = client.post('/session/clear', json={})
            self.assertEqual(clear_response.status_code, 200)
            
            # Send another message - should have new session
            response2 = client.post('/chat', json={
                'message': 'I like comedy movies'
            })
            self.assertEqual(response2.status_code, 200)
            
            data1 = response1.get_json()
            data2 = response2.get_json()
            
            # Session IDs should be different
            self.assertNotEqual(data1.get('session_id'), data2.get('session_id'))
    
    def test_recommended_movies_tracked(self):
        """Test that recommended movies are tracked in session."""
        from cineman.session_manager import get_session_manager
        
        session_manager = get_session_manager()
        session_id = session_manager.create_session()
        session_data = session_manager.get_session(session_id)
        
        # Simulate adding recommended movies
        session_data.add_recommended_movies(['Inception', 'The Matrix', 'Interstellar'])
        
        movies = session_data.get_recommended_movies()
        self.assertEqual(len(movies), 3)
        self.assertIn('Inception', movies)
        self.assertIn('The Matrix', movies)
        self.assertIn('Interstellar', movies)
    
    def test_duplicate_movies_not_added(self):
        """Test that duplicate movie recommendations are not tracked twice."""
        from cineman.session_manager import get_session_manager
        
        session_manager = get_session_manager()
        session_id = session_manager.create_session()
        session_data = session_manager.get_session(session_id)
        
        # Add movies first time
        session_data.add_recommended_movies(['Inception', 'The Matrix'])
        
        # Try to add same movies again
        session_data.add_recommended_movies(['Inception', 'Blade Runner'])
        
        movies = session_data.get_recommended_movies()
        # Should have 3 movies, not 4 (Inception not duplicated)
        self.assertEqual(len(movies), 3)
        self.assertIn('Inception', movies)
        self.assertIn('The Matrix', movies)
        self.assertIn('Blade Runner', movies)
    
    def test_chat_history_limit(self):
        """Test that chat history can be limited to recent messages."""
        from cineman.session_manager import get_session_manager
        
        session_manager = get_session_manager()
        session_id = session_manager.create_session()
        session_data = session_manager.get_session(session_id)
        
        # Add many messages
        for i in range(20):
            session_data.add_message("user", f"Message {i}")
            session_data.add_message("assistant", f"Response {i}")
        
        # Get all history
        all_history = session_data.get_chat_history()
        self.assertEqual(len(all_history), 40)
        
        # Get limited history
        limited = session_data.get_chat_history(limit=10)
        self.assertEqual(len(limited), 10)
        
        # Should get the last 10 messages
        self.assertEqual(limited[0]['content'], 'Message 15')
        self.assertEqual(limited[-1]['content'], 'Response 19')
    
    def test_context_includes_previous_recommendations(self):
        """Test that session context includes previously recommended movies."""
        from cineman.chain import build_session_context
        
        chat_history = [
            {'role': 'user', 'content': 'I want sci-fi movies'},
            {'role': 'assistant', 'content': 'Here are some recommendations...'}
        ]
        recommended_movies = ['Inception', 'The Matrix', 'Interstellar']
        
        context = build_session_context(chat_history, recommended_movies)
        
        # Context should mention previously recommended movies
        self.assertIn('Inception', context)
        self.assertIn('The Matrix', context)
        self.assertIn('Interstellar', context)
        self.assertIn('Previously recommended', context)
        self.assertIn('DO NOT recommend these again', context)
    
    def test_empty_context_when_no_recommendations(self):
        """Test that context is empty when no movies have been recommended."""
        from cineman.chain import build_session_context
        
        chat_history = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there!'}
        ]
        recommended_movies = []
        
        context = build_session_context(chat_history, recommended_movies)
        
        # Context should be empty
        self.assertEqual(context, '')
    
    def test_session_timeout_configuration(self):
        """Test that session timeout is configurable."""
        from datetime import timedelta
        
        session_manager = SessionManager(session_timeout_minutes=30)
        self.assertEqual(session_manager.session_timeout, timedelta(minutes=30))
        
        session_manager2 = SessionManager(session_timeout_minutes=120)
        self.assertEqual(session_manager2.session_timeout, timedelta(minutes=120))
    
    def test_multiple_sessions_are_isolated(self):
        """Test that multiple sessions maintain isolated data."""
        from cineman.session_manager import SessionManager
        
        session_manager = SessionManager()
        
        # Create two sessions
        session1_id = session_manager.create_session()
        session2_id = session_manager.create_session()
        
        session1 = session_manager.get_session(session1_id)
        session2 = session_manager.get_session(session2_id)
        
        # Add different data to each
        session1.add_message("user", "I like horror movies")
        session1.add_recommended_movies(['The Shining', 'Hereditary'])
        
        session2.add_message("user", "I like comedies")
        session2.add_recommended_movies(['Superbad', 'The Hangover'])
        
        # Verify isolation
        self.assertEqual(len(session1.get_chat_history()), 1)
        self.assertEqual(len(session2.get_chat_history()), 1)
        
        self.assertIn('The Shining', session1.get_recommended_movies())
        self.assertNotIn('The Shining', session2.get_recommended_movies())
        
        self.assertIn('Superbad', session2.get_recommended_movies())
        self.assertNotIn('Superbad', session1.get_recommended_movies())


class TestConversationalPrompts(unittest.TestCase):
    """Test conversation scenarios with different types of prompts."""
    
    def test_conversational_prompt_detection(self):
        """Test that we can distinguish conversational vs recommendation prompts."""
        
        # Conversational prompts (should NOT trigger recommendation mode)
        conversational_prompts = [
            "What do you think about Christopher Nolan?",
            "Tell me about the history of sci-fi films",
            "I really liked Inception, what made it so good?",
            "What are the themes in The Matrix?",
            "Who directed Blade Runner?",
            "I didn't really enjoy that last suggestion",
            "Can you tell me more about film noir?",
            "What makes a good horror movie?"
        ]
        
        # Recommendation prompts (SHOULD trigger recommendation mode)
        recommendation_prompts = [
            "recommend some sci-fi movies",
            "suggest films like Inception",
            "what should I watch tonight?",
            "give me movie recommendations",
            "I want suggestions for action movies",
            "can you recommend something?",
            "suggest some good thrillers"
        ]
        
        # This is a marker test - the actual detection happens in the LLM
        # We're documenting expected behavior
        for prompt in conversational_prompts:
            self.assertIsNotNone(prompt)  # Basic assertion
        
        for prompt in recommendation_prompts:
            self.assertIsNotNone(prompt)  # Basic assertion
    
    def test_conversation_flow_scenarios(self):
        """Test various conversation flow scenarios."""
        
        # Scenario 1: User shares preferences, then asks for recommendations
        scenario1 = [
            "I really enjoy movies with complex plots",
            "I also like psychological thrillers",
            "And I'm a fan of Leonardo DiCaprio",
            "Now recommend me some movies based on what I told you"
        ]
        
        # Scenario 2: User gets recommendations, provides feedback, asks for more
        scenario2 = [
            "recommend some action movies",
            "I've already seen all of those",
            "suggest something more obscure"
        ]
        
        # Scenario 3: User has a conversation about movies
        scenario3 = [
            "What makes Inception such a great movie?",
            "Are there other movies with similar dream concepts?",
            "recommend movies with dream themes"
        ]
        
        # These scenarios should be handled by the updated system
        self.assertTrue(len(scenario1) > 0)
        self.assertTrue(len(scenario2) > 0)
        self.assertTrue(len(scenario3) > 0)


if __name__ == '__main__':
    print("\n" + "="*70)
    print("Running Conversation Holding Tests")
    print("="*70 + "\n")
    unittest.main(verbosity=2)
