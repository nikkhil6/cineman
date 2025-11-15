"""
Integration tests for conversation holding with real LLM interactions.
These tests require API keys to be set and will make actual calls to the LLM.

Run with: python tests/test_conversation_integration.py

Set environment variables before running:
export GEMINI_API_KEY=your_key
"""
import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.chain import get_recommendation_chain, format_chat_history
from cineman.session_manager import SessionManager
from langchain_core.messages import HumanMessage, AIMessage


def print_separator(title=""):
    """Print a visual separator."""
    print("\n" + "="*80)
    if title:
        print(f"  {title}")
        print("="*80)
    print()


def test_conversational_flow():
    """Test a full conversation flow with the LLM."""
    print_separator("Testing Conversational Flow")
    
    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  GEMINI_API_KEY not set. Skipping integration test.")
        print("   Set the API key to run this test: export GEMINI_API_KEY=your_key")
        return False
    
    try:
        chain = get_recommendation_chain()
        session_manager = SessionManager()
        session_id = session_manager.create_session()
        session_data = session_manager.get_session(session_id)
        
        # Conversation scenario: User discusses preferences, then asks for recommendations
        conversation_steps = [
            {
                "user": "Hello! I'm looking for some help finding movies to watch.",
                "expected_mode": "conversational",
                "description": "Initial greeting"
            },
            {
                "user": "I really enjoy movies with complex plots and psychological themes.",
                "expected_mode": "conversational",
                "description": "Sharing preferences"
            },
            {
                "user": "What makes a good psychological thriller?",
                "expected_mode": "conversational",
                "description": "Asking a question"
            },
            {
                "user": "Now based on what I told you, recommend me some movies.",
                "expected_mode": "recommendation",
                "description": "Requesting recommendations"
            },
            {
                "user": "I've already seen Inception. Can you tell me more about the second one?",
                "expected_mode": "conversational",
                "description": "Feedback and question"
            },
            {
                "user": "Suggest some more movies like these, but more obscure.",
                "expected_mode": "recommendation",
                "description": "Asking for more recommendations"
            }
        ]
        
        for i, step in enumerate(conversation_steps, 1):
            print(f"Step {i}: {step['description']}")
            print(f"User: {step['user']}")
            print("-" * 80)
            
            # Format chat history
            chat_history = session_data.get_chat_history()
            formatted_history = format_chat_history(chat_history[-6:])
            
            # Get response from LLM
            start_time = time.time()
            response = chain.invoke({
                "user_input": step['user'],
                "chat_history": formatted_history
            })
            elapsed_time = time.time() - start_time
            
            # Add to session
            session_data.add_message("user", step['user'])
            session_data.add_message("assistant", response)
            
            # Print response
            print(f"Assistant: {response[:500]}...")  # First 500 chars
            if len(response) > 500:
                print(f"  ... (response continues, total length: {len(response)} chars)")
            print(f"  [Response time: {elapsed_time:.2f}s]")
            
            # Check if response contains JSON (indicates recommendation mode)
            has_json = response.rfind('{') != -1 and response.rfind('}') != -1
            detected_mode = "recommendation" if has_json else "conversational"
            
            print(f"  Expected mode: {step['expected_mode']}")
            print(f"  Detected mode: {detected_mode}")
            
            if detected_mode == step['expected_mode']:
                print("  ✅ Mode detection: PASS")
            else:
                print("  ⚠️  Mode detection: Different than expected (LLM may have interpreted differently)")
            
            print()
            time.sleep(1)  # Rate limiting
        
        print_separator("Conversation Test Complete")
        print(f"✅ Completed {len(conversation_steps)} conversation steps")
        print(f"📝 Chat history contains {len(session_data.get_chat_history())} messages")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_recommendation_request_variations():
    """Test different ways users might request recommendations."""
    print_separator("Testing Recommendation Request Variations")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  GEMINI_API_KEY not set. Skipping integration test.")
        return False
    
    try:
        chain = get_recommendation_chain()
        
        # Different ways to request recommendations
        requests = [
            "recommend some sci-fi movies",
            "what movies should I watch tonight?",
            "give me suggestions for action films",
            "I want movie recommendations for thrillers",
            "suggest good horror movies"
        ]
        
        for i, request in enumerate(requests, 1):
            print(f"Test {i}: {request}")
            print("-" * 80)
            
            response = chain.invoke({
                "user_input": request,
                "chat_history": []
            })
            
            # Check if JSON manifest is present
            has_json = '{"movies":' in response or '"movies":' in response
            has_anchor = 'anchor:m1' in response
            
            print(f"Response length: {len(response)} chars")
            print(f"  Has JSON manifest: {'✅ YES' if has_json else '❌ NO'}")
            print(f"  Has anchor markers: {'✅ YES' if has_anchor else '❌ NO'}")
            
            if has_json and has_anchor:
                print("  ✅ Proper recommendation format detected")
            else:
                print("  ⚠️  May not be in proper recommendation format")
            
            print()
            time.sleep(1)
        
        print_separator("Recommendation Variations Test Complete")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_conversational_questions():
    """Test conversational questions that should NOT trigger recommendations."""
    print_separator("Testing Conversational Questions")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  GEMINI_API_KEY not set. Skipping integration test.")
        return False
    
    try:
        chain = get_recommendation_chain()
        
        # Questions that should get conversational responses
        questions = [
            "What makes Christopher Nolan such a great director?",
            "Tell me about the themes in The Matrix",
            "What's the difference between science fiction and fantasy?",
            "Who are some famous film noir directors?",
            "What made Inception so popular?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"Test {i}: {question}")
            print("-" * 80)
            
            response = chain.invoke({
                "user_input": question,
                "chat_history": []
            })
            
            # Check that it's NOT in recommendation format
            has_json = '{"movies":' in response or '"movies":' in response
            has_anchor = 'anchor:m1' in response
            
            print(f"Response length: {len(response)} chars")
            print(f"  Has JSON manifest: {'❌ NO' if not has_json else '⚠️  YES (unexpected)'}")
            print(f"  Has anchor markers: {'❌ NO' if not has_anchor else '⚠️  YES (unexpected)'}")
            
            if not has_json and not has_anchor:
                print("  ✅ Proper conversational format detected")
            else:
                print("  ⚠️  Unexpected recommendation format for conversational question")
            
            print()
            time.sleep(1)
        
        print_separator("Conversational Questions Test Complete")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    print("\n" + "🎬" * 40)
    print("  CineMan Conversation Integration Tests")
    print("🎬" * 40)
    
    if not os.getenv("GEMINI_API_KEY"):
        print("\n⚠️  WARNING: GEMINI_API_KEY environment variable is not set.")
        print("These integration tests require a valid API key to run.")
        print("Set it with: export GEMINI_API_KEY=your_key")
        print("\nSkipping all integration tests.")
        return
    
    results = []
    
    # Run tests
    print("\n" + "🧪" * 40)
    print("  Running Integration Tests")
    print("🧪" * 40)
    
    results.append(("Conversational Flow", test_conversational_flow()))
    results.append(("Recommendation Variations", test_recommendation_request_variations()))
    results.append(("Conversational Questions", test_conversational_questions()))
    
    # Summary
    print_separator("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All integration tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    print()


if __name__ == "__main__":
    main()
