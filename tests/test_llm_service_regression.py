import pytest
from unittest.mock import MagicMock, patch
from cineman.services.llm_service import LLMService

class TestLLMServiceRegression:

    @patch('cineman.services.llm_service.get_recommendation_chain')
    @patch('cineman.services.llm_service.validate_movie_list')
    @patch('cineman.services.llm_service.LLMService._get_session_recommendations')
    def test_llm_service_single_invocation_regression(self, mock_get_recs, mock_validate, mock_get_chain):
        """
        Regression test to ensure process_chat_request only calls the LLM chain once.
        This prevents unnecessary latency and API costs.
        """
        # Setup mocks
        mock_chain = MagicMock()
        mock_get_chain.return_value = mock_chain
        
        # Mock the structured output return (impersonating ChatResponse Pydantic object)
        mock_response = MagicMock()
        mock_response.response_text = "Here is a movie recommendation."
        mock_response.movies = []
        mock_chain.invoke.return_value = mock_response
        
        # Other dependencies
        mock_get_recs.return_value = []
        mock_validate.return_value = ([], [], {"total_checked": 0, "valid_count": 0, "dropped_count": 0, "avg_latency_ms": 0})
        
        # Initialize service (using the patch ensures the mock chain is used)
        # We create a new instance to avoid singleton state issues in tests
        service = LLMService()
        service.chain = mock_chain
        
        # Execute request
        service.process_chat_request("Suggest a sci-fi movie", [], "session_abc_123")
        
        # ASSERT: Chain.invoke should be called exactly once
        assert mock_chain.invoke.call_count == 1, f"Expected 1 LLM call, but got {mock_chain.invoke.call_count}"
        
        # Verify the input includes the System Context placeholder if context exists
        # If we add context in a future test case, it would go here.
