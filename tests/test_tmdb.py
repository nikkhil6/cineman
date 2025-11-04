import os
import sys
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the core function we are testing from the cineman.tools module
try:
    from cineman.tools.tmdb import get_movie_poster_core
except ImportError:
    print("FATAL ERROR: Could not import get_movie_poster_core. Ensure cineman package is installed.")
    sys.exit(1)

# --- Test Functions ---

def run_test(title: str):
    """Executes the tool function and prints the result for inspection."""
    print(f"\n--- Testing Movie: '{title}' ---")
    
    # Check for API Key setup before calling the function
    if not os.getenv("TMDB_API_KEY"):
        print("❌ TEST ABORTED: TMDB_API_KEY environment variable is missing.")
        return

    # Execute the core function
    result_str = get_movie_poster_core(title)
    
    try:
        # Convert the string result back to a Python dictionary for easy inspection
        result = json.loads(result_str)
        print("✅ Success: Tool returned valid JSON.")
        
        # Check if the search was successful
        if result.get("status") == "success":
            print(f"   Status: {result['status']}")
            print(f"   Year: {result.get('year')}")
            print(f"   Poster URL: {result.get('poster_url')}")
            
            # Additional check: Does the URL look like a valid poster link?
            if result.get('poster_url') and result['poster_url'].startswith("https://image.tmdb.org/t/p/w500"):
                print("   ✅ URL Format: Correct.")
            else:
                print("   ❌ URL Format: Incorrect or missing poster path.")
                
        else:
            print(f"❌ Failure: Status '{result.get('status')}'")
            print(f"   Error/Message: {result_str}")

    except json.JSONDecodeError:
        print("❌ FAILURE: Tool returned non-JSON data.")
        print(f"   Raw Output: {result_str}")


if __name__ == "__main__":
    
    # --- Execute Test Cases ---
    
    # 1. Successful Case (A well-known movie)
    run_test("Interstellar")
    
    # 2. Movie Not Found Case
    run_test("A Movie That Does Not Exist 123456")
    
    # 3. Simple Search Ambiguity Case
    run_test("Dune")
