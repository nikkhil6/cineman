#!/usr/bin/env python3
"""
Interactive conversation testing script for CineMan.
Run this to manually test the conversation holding feature.

Usage: python scripts/test_conversation.py
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.chain import get_recommendation_chain, format_chat_history
from cineman.session_manager import SessionManager


def print_banner():
    """Print welcome banner."""
    print("\n" + "🎬" * 40)
    print("  CineMan - Interactive Conversation Tester")
    print("🎬" * 40)
    print("\nThis tool lets you test the conversation holding feature.")
    print("You can have a conversation with CineMan about movies!\n")
    print("Commands:")
    print("  - Type your message to chat")
    print("  - Type 'new' to start a new session")
    print("  - Type 'history' to see chat history")
    print("  - Type 'movies' to see recommended movies")
    print("  - Type 'quit' or 'exit' to quit")
    print("\n" + "-" * 80 + "\n")


def print_message(role, message):
    """Print a formatted message."""
    if role == "user":
        print(f"\n👤 You: {message}")
    else:
        print(f"\n🤖 CineMan:")
        print(message)
    print("-" * 80)


def main():
    """Run the interactive conversation tester."""
    
    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("\n❌ ERROR: GEMINI_API_KEY environment variable is not set.")
        print("Please set it with: export GEMINI_API_KEY=your_key")
        sys.exit(1)
    
    print_banner()
    
    try:
        # Initialize chain and session
        print("⏳ Initializing CineMan...")
        chain = get_recommendation_chain()
        session_manager = SessionManager()
        session_id = session_manager.create_session()
        session_data = session_manager.get_session(session_id)
        print("✅ Ready to chat!\n")
        
        while True:
            # Get user input
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye! 👋")
                break
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye! 👋")
                break
            
            elif user_input.lower() == 'new':
                # Start new session
                session_id = session_manager.create_session()
                session_data = session_manager.get_session(session_id)
                print("\n✨ Started a new session! Previous conversation cleared.")
                continue
            
            elif user_input.lower() == 'history':
                # Show chat history
                history = session_data.get_chat_history()
                print(f"\n📝 Chat History ({len(history)} messages):")
                for i, msg in enumerate(history, 1):
                    role = msg['role']
                    content = msg['content']
                    # Truncate long messages
                    if len(content) > 100:
                        content = content[:100] + "..."
                    print(f"  {i}. [{role}] {content}")
                continue
            
            elif user_input.lower() == 'movies':
                # Show recommended movies
                movies = session_data.get_recommended_movies()
                if movies:
                    print(f"\n🎬 Recommended Movies ({len(movies)}):")
                    for i, movie in enumerate(movies, 1):
                        print(f"  {i}. {movie}")
                else:
                    print("\n📭 No movies recommended yet in this session.")
                continue
            
            # Process message through LLM
            print("\n⏳ CineMan is thinking...")
            
            # Format chat history
            chat_history = session_data.get_chat_history()
            formatted_history = format_chat_history(chat_history[-6:])
            
            try:
                # Get response from LLM
                response = chain.invoke({
                    "user_input": user_input,
                    "chat_history": formatted_history
                })
                
                # Add to session
                session_data.add_message("user", user_input)
                session_data.add_message("assistant", response)
                
                # Extract and track movies if present
                if '{"movies":' in response or '"movies":' in response:
                    # Try to extract movie titles
                    import json
                    try:
                        json_start = response.rfind('{')
                        if json_start != -1:
                            json_str = response[json_start:].strip()
                            manifest = json.loads(json_str)
                            if 'movies' in manifest:
                                movie_titles = [m.get('title', '') for m in manifest['movies'] if m.get('title')]
                                session_data.add_recommended_movies(movie_titles)
                                print(f"📌 Added {len(movie_titles)} movies to tracking")
                    except:
                        pass
                
                # Print response
                print_message("assistant", response)
                
            except Exception as e:
                print(f"\n❌ Error getting response: {e}")
                import traceback
                traceback.print_exc()
    
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye! 👋")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
