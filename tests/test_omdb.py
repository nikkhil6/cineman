import os
import sys
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- CRUCIAL: Ensure the OMDB_API_KEY is set in your terminal first ---
if not os.getenv("OMDB_API_KEY"):
    print(
        "❌ ERROR: OMDB_API_KEY environment variable is missing. Please set it before running."
    )
    sys.exit(1)

# Import the function we are now using for facts and posters
try:
    from cineman.tools.omdb import fetch_omdb_data_core
except ImportError:
    print(
        "❌ FATAL: Could not import fetch_omdb_data_core. Ensure cineman package is installed."
    )
    sys.exit(1)


def run_test_case(title: str):
    """Executes the tool function and checks the output format."""
    print(f"\n--- Testing Movie: '{title}' ---")

    # Execute the core function
    result_str = fetch_omdb_data_core(title)

    try:
        # The result must be a JSON string that Python can load
        result = json.loads(result_str.replace("'", '"'))

        print("✅ SUCCESS: Tool returned valid data.")

        # --- Verification Checks ---
        print(f"   Title Found: {result.get('Title', 'N/A')}")
        print(f"   IMDb Rating: {result.get('IMDb_Rating', 'N/A')}")

        poster_url = result.get("Poster_URL", "N/A")

        if poster_url.startswith("http"):
            print("   ✅ Poster URL: Found (URL starts with http)")
            print(f"   [Link: {poster_url[:50]}...]")
        elif poster_url == "N/A" or "not found" in result.get("status", "").lower():
            print("   ❌ Poster URL: Not found (Expected for missing movie).")
        else:
            print("   ❌ Poster URL: Missing or Invalid format.")

    except json.JSONDecodeError:
        print("❌ FAILURE: Tool returned malformed JSON.")
        print(f"   Raw Output: {result_str}")


# =================================================================
if __name__ == "__main__":

    # 1. Successful Case (A well-known movie)
    run_test_case("Interstellar")

    # 2. Ambiguity Case (Should resolve to the most popular/latest one)
    run_test_case("Dune")

    # 3. Movie Not Found Case (Should trigger the error handling in omdb_tool.py)
    run_test_case("A Movie That Does Not Exist 123456")
