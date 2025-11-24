"""
Tests for LLM hallucination validation module.
"""

import pytest
from unittest.mock import patch, MagicMock
from cineman.validation import (
    normalize_text,
    normalize_year,
    calculate_title_similarity,
    validate_llm_recommendation,
    validate_movie_list,
    ValidationResult
)


class TestNormalization:
    """Test text and data normalization functions."""
    
    def test_normalize_text_basic(self):
        """Test basic text normalization."""
        assert normalize_text("The Matrix") == "the matrix"
        assert normalize_text("INCEPTION") == "inception"
        assert normalize_text("  Pulp   Fiction  ") == "pulp fiction"
    
    def test_normalize_text_punctuation(self):
        """Test punctuation removal."""
        assert normalize_text("The Dark Knight: Returns!") == "the dark knight returns"
        assert normalize_text("Spider-Man") == "spider-man"  # Keep hyphens
        assert normalize_text("Ocean's Eleven") == "ocean's eleven"  # Keep apostrophes
    
    def test_normalize_text_empty(self):
        """Test empty string handling."""
        assert normalize_text("") == ""
        assert normalize_text(None) == ""
    
    def test_normalize_year_basic(self):
        """Test year normalization."""
        assert normalize_year("2010") == "2010"
        assert normalize_year("1999") == "1999"
    
    def test_normalize_year_range(self):
        """Test year range extraction."""
        assert normalize_year("2010-2012") == "2010"
        assert normalize_year("2010-") == "2010"
    
    def test_normalize_year_with_text(self):
        """Test year extraction from text."""
        assert normalize_year("2010 (TV Movie)") == "2010"
        assert normalize_year("Released in 2010") == "2010"
    
    def test_normalize_year_invalid(self):
        """Test invalid year handling."""
        assert normalize_year("N/A") is None
        assert normalize_year("") is None
        assert normalize_year(None) is None


class TestTitleSimilarity:
    """Test title similarity calculation."""
    
    def test_exact_match(self):
        """Test exact title matches."""
        assert calculate_title_similarity("Inception", "Inception") == 1.0
        assert calculate_title_similarity("The Matrix", "The Matrix") == 1.0
    
    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        assert calculate_title_similarity("INCEPTION", "inception") == 1.0
        assert calculate_title_similarity("The Matrix", "the matrix") == 1.0
    
    def test_substring_match(self):
        """Test substring/containment matching."""
        score = calculate_title_similarity("The Matrix", "The Matrix Reloaded")
        assert 0.8 <= score <= 1.0  # Should be high but not perfect
    
    def test_word_overlap(self):
        """Test word-level similarity."""
        score = calculate_title_similarity("The Dark Knight", "The Dark Knight Rises")
        assert score > 0.6  # Significant overlap
        
        score = calculate_title_similarity("Star Wars", "Star Trek")
        assert 0.3 < score < 0.7  # Partial overlap
    
    def test_no_match(self):
        """Test completely different titles."""
        score = calculate_title_similarity("Inception", "The Matrix")
        assert score == 0.0


class TestValidationWithMocks:
    """Test validation logic with mocked API responses."""
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_validate_real_movie_both_sources(self, mock_omdb, mock_tmdb):
        """Test validation of a real movie found in both sources."""
        # Mock TMDB response
        mock_tmdb.return_value = {
            "status": "success",
            "title": "Inception",
            "year": "2010",
            "tmdb_id": 27205,
            "vote_average": 8.3,
            "vote_count": 35000
        }
        
        # Mock OMDb response
        mock_omdb.return_value = {
            "status": "success",
            "Title": "Inception",
            "Year": "2010",
            "Director": "Christopher Nolan",
            "IMDb_Rating": "8.8"
        }
        
        result = validate_llm_recommendation(
            title="Inception",
            year="2010",
            director="Christopher Nolan"
        )
        
        assert result.is_valid is True
        assert result.confidence >= 0.9
        assert result.source == "both"
        assert result.matched_title == "Inception"
        assert result.matched_year == "2010"
        assert result.matched_director == "Christopher Nolan"
        assert result.should_drop is False
        assert len(result.corrections) == 0
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_validate_hallucinated_movie(self, mock_omdb, mock_tmdb):
        """Test validation fails for hallucinated/fake movie."""
        # Mock TMDB - not found
        mock_tmdb.return_value = {
            "status": "not_found",
            "title": None,
            "year": None
        }
        
        # Mock OMDb - not found
        mock_omdb.return_value = {
            "status": "not_found",
            "Title": None,
            "Year": None,
            "error": "Movie not found!"
        }
        
        result = validate_llm_recommendation(
            title="The Fake Movie That Doesn't Exist",
            year="2025",
            director="John Doe"
        )
        
        assert result.is_valid is False
        assert result.confidence == 0.0
        assert result.source == "none"
        assert result.should_drop is True
        assert "not found" in result.error_message.lower()
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_validate_movie_with_typo(self, mock_omdb, mock_tmdb):
        """Test validation corrects minor typos."""
        # Mock TMDB response with correct spelling
        mock_tmdb.return_value = {
            "status": "success",
            "title": "The Shawshank Redemption",
            "year": "1994",
            "tmdb_id": 278
        }
        
        # Mock OMDb response with correct spelling
        mock_omdb.return_value = {
            "status": "success",
            "Title": "The Shawshank Redemption",
            "Year": "1994",
            "Director": "Frank Darabont"
        }
        
        # LLM provided slightly misspelled title
        result = validate_llm_recommendation(
            title="The Shawshank Redemtion",  # Typo in "Redemption"
            year="1994",
            director="Frank Darabont"
        )
        
        # Should still validate with good confidence (0.7+)
        assert result.is_valid is True
        assert result.confidence >= 0.7
        # Should have correction
        assert "title" in result.corrections
        assert result.corrections["title"][1] == "The Shawshank Redemption"
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_validate_obscure_movie_single_source(self, mock_omdb, mock_tmdb):
        """Test validation accepts obscure movie found in only one source."""
        # Mock TMDB - found
        mock_tmdb.return_value = {
            "status": "success",
            "title": "Primer",
            "year": "2004",
            "tmdb_id": 14337
        }
        
        # Mock OMDb - not found (obscure movie)
        mock_omdb.return_value = {
            "status": "not_found",
            "error": "Movie not found!"
        }
        
        result = validate_llm_recommendation(
            title="Primer",
            year="2004"
        )
        
        # Should still be valid with reduced confidence
        assert result.is_valid is True
        assert 0.5 <= result.confidence < 0.9
        assert result.source == "tmdb"
        assert result.should_drop is False
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_validate_wrong_year(self, mock_omdb, mock_tmdb):
        """Test validation catches wrong year."""
        # Mock responses with correct year
        mock_tmdb.return_value = {
            "status": "success",
            "title": "The Matrix",
            "year": "1999",
            "tmdb_id": 603
        }
        
        mock_omdb.return_value = {
            "status": "success",
            "Title": "The Matrix",
            "Year": "1999",
            "Director": "Lana Wachowski, Lilly Wachowski"
        }
        
        # LLM provided wrong year
        result = validate_llm_recommendation(
            title="The Matrix",
            year="2000",  # Wrong year
            director="The Wachowskis"
        )
        
        assert result.is_valid is True  # Still valid movie
        assert "year" in result.corrections  # But year corrected
        assert result.corrections["year"][1] == "1999"
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_validate_partial_title_match(self, mock_omdb, mock_tmdb):
        """Test validation handles partial title matches."""
        # Mock TMDB
        mock_tmdb.return_value = {
            "status": "success",
            "title": "The Lord of the Rings: The Fellowship of the Ring",
            "year": "2001",
            "tmdb_id": 120
        }
        
        # Mock OMDb
        mock_omdb.return_value = {
            "status": "success",
            "Title": "The Lord of the Rings: The Fellowship of the Ring",
            "Year": "2001",
            "Director": "Peter Jackson"
        }
        
        # LLM provided shortened title
        result = validate_llm_recommendation(
            title="The Fellowship of the Ring",
            year="2001"
        )
        
        # Should still validate with good confidence
        assert result.is_valid is True
        assert result.confidence >= 0.7


class TestValidateMovieList:
    """Test batch validation of movie lists."""
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_validate_mixed_list(self, mock_omdb, mock_tmdb):
        """Test validating a list with real and fake movies."""
        
        def tmdb_side_effect(title, year=None):
            if "Inception" in title:
                return {
                    "status": "success",
                    "title": "Inception",
                    "year": "2010",
                    "tmdb_id": 27205
                }
            elif "Matrix" in title:
                return {
                    "status": "success",
                    "title": "The Matrix",
                    "year": "1999",
                    "tmdb_id": 603
                }
            else:
                return {"status": "not_found"}
        
        def omdb_side_effect(title, year=None):
            if "Inception" in title:
                return {
                    "status": "success",
                    "Title": "Inception",
                    "Year": "2010",
                    "Director": "Christopher Nolan"
                }
            elif "Matrix" in title:
                return {
                    "status": "success",
                    "Title": "The Matrix",
                    "Year": "1999",
                    "Director": "Lana Wachowski, Lilly Wachowski"
                }
            else:
                return {"status": "not_found"}
        
        mock_tmdb.side_effect = tmdb_side_effect
        mock_omdb.side_effect = omdb_side_effect
        
        movies = [
            {"title": "Inception", "year": "2010", "director": "Christopher Nolan"},
            {"title": "The Matrix", "year": "1999", "director": "The Wachowskis"},
            {"title": "Fake Movie XYZ", "year": "2025", "director": "Nobody"}
        ]
        
        valid, dropped, summary = validate_movie_list(movies, session_id="test_123")
        
        assert len(valid) == 2
        assert len(dropped) == 1
        assert summary["total_checked"] == 3
        assert summary["valid_count"] == 2
        assert summary["dropped_count"] == 1
        assert summary["avg_latency_ms"] > 0
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_validate_empty_list(self, mock_omdb, mock_tmdb):
        """Test validating empty movie list."""
        valid, dropped, summary = validate_movie_list([])
        
        assert len(valid) == 0
        assert len(dropped) == 0
        assert summary["total_checked"] == 0


class TestValidationPerformance:
    """Test validation performance requirements."""
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_validation_latency_target(self, mock_omdb, mock_tmdb):
        """Test that validation meets <400ms average latency target."""
        # Mock fast responses
        mock_tmdb.return_value = {
            "status": "success",
            "title": "Test Movie",
            "year": "2020",
            "tmdb_id": 1
        }
        
        mock_omdb.return_value = {
            "status": "success",
            "Title": "Test Movie",
            "Year": "2020",
            "Director": "Test Director"
        }
        
        # Run validation
        result = validate_llm_recommendation(
            title="Test Movie",
            year="2020",
            director="Test Director"
        )
        
        # Check latency is recorded
        assert result.latency_ms > 0
        
        # Note: With mocked APIs, latency will be very low
        # In real scenarios with caching, should be <400ms
        assert result.latency_ms < 1000  # Generous upper bound for test


class TestValidationWithRealAPIs:
    """Integration tests with real APIs (requires API keys)."""
    
    @pytest.mark.integration
    def test_validate_real_movie_inception(self):
        """Test validation with real API call for Inception."""
        # This test requires valid TMDB_API_KEY and OMDB_API_KEY
        import os
        tmdb_key = os.getenv("TMDB_API_KEY", "")
        omdb_key = os.getenv("OMDB_API_KEY", "")
        # Skip if keys are missing or are test placeholders
        if not tmdb_key or not omdb_key or tmdb_key == "test" or omdb_key == "test":
            pytest.skip("Real API keys not configured")
        
        result = validate_llm_recommendation(
            title="Inception",
            year="2010",
            director="Christopher Nolan",
            recommendation_id="integration_test_1"
        )
        
        assert result.is_valid is True
        assert result.confidence >= 0.9
        assert result.source in ["both", "tmdb", "omdb"]
        assert result.should_drop is False
        assert result.latency_ms < 5000  # Should be fast with real APIs
    
    @pytest.mark.integration
    def test_validate_fake_movie(self):
        """Test validation fails for completely fake movie."""
        import os
        tmdb_key = os.getenv("TMDB_API_KEY", "")
        omdb_key = os.getenv("OMDB_API_KEY", "")
        # Skip if keys are missing or are test placeholders
        if not tmdb_key or not omdb_key or tmdb_key == "test" or omdb_key == "test":
            pytest.skip("Real API keys not configured")
        
        result = validate_llm_recommendation(
            title="The Completely Fabricated Movie That Never Existed 12345",
            year="2099",
            director="Fake Director",
            recommendation_id="integration_test_2"
        )
        
        assert result.is_valid is False
        assert result.confidence == 0.0
        assert result.should_drop is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
