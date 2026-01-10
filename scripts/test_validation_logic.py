import sys
import os
sys.path.append(os.getcwd())

from cineman.validation import validate_llm_recommendation, validate_movie_list
import json

def test_single_validation():
    print("Testing single movie validation: 'Inception' (2010)")
    result = validate_llm_recommendation(
        title="Inception",
        year="2010",
        director="Christopher Nolan",
        recommendation_id="test_1"
    )
    print(f"Result: is_valid={result.is_valid}, confidence={result.confidence:.2f}, source={result.source}")
    print(f"Matched: {result.matched_title} ({result.matched_year})")
    print(f"TMDB Found: {result.tmdb_data.get('found') if result.tmdb_data else 'None'}")
    print(f"OMDB Found: {result.omdb_data.get('found') if result.omdb_data else 'None'}")
    
def test_list_validation():
    print("\nTesting movie list validation...")
    movies = [
        {"title": "Interstellar", "year": "2014", "director": "Christopher Nolan"},
        {"title": "The Matrix", "year": "1999", "director": "Lana Wachowski"}
    ]
    valid, dropped, summary = validate_movie_list(movies, session_id="test_session")
    print(f"Summary: {summary}")
    print(f"Valid count: {len(valid)}")
    print(f"Dropped count: {len(dropped)}")
    if dropped:
        print(f"Drop reason for first dropped: {dropped[0].get('drop_reason')}")

if __name__ == "__main__":
    try:
        test_single_validation()
        test_list_validation()
    except Exception as e:
        import traceback
        traceback.print_exc()
