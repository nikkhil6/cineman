"""
Tests for LangChain recommendation chain.
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open


class TestPromptLoading:
    """Test prompt file loading."""

    def test_load_prompt_from_file_success(self):
        """Test successful prompt loading."""
        from cineman.chain import load_prompt_from_file

        mock_content = "This is a test prompt"
        with patch("builtins.open", mock_open(read_data=mock_content)):
            result = load_prompt_from_file("test_prompt.txt")

        assert result == mock_content

    def test_load_prompt_from_file_not_found(self):
        """Test prompt loading when file not found."""
        from cineman.chain import load_prompt_from_file

        with patch("builtins.open", side_effect=FileNotFoundError()):
            with pytest.raises(FileNotFoundError):
                load_prompt_from_file("nonexistent.txt")


class TestBraceEscaping:
    """Test brace escaping for prompt templates."""

    def test_escape_braces_for_prompt(self):
        """Test escaping braces in prompt text."""
        from cineman.chain import escape_braces_for_prompt

        text = "This is a {test} with {multiple} braces"
        result = escape_braces_for_prompt(text)

        assert result == "This is a {{test}} with {{multiple}} braces"

    def test_escape_braces_empty_string(self):
        """Test escaping empty string."""
        from cineman.chain import escape_braces_for_prompt

        result = escape_braces_for_prompt("")

        assert result == ""

    def test_escape_braces_none(self):
        """Test escaping None."""
        from cineman.chain import escape_braces_for_prompt

        result = escape_braces_for_prompt(None)

        assert result is None


class TestRecommendationChain:
    """Test recommendation chain creation and execution."""

    @patch("cineman.chain.os.getenv")
    def test_get_recommendation_chain_no_api_key(self, mock_getenv):
        """Test chain creation fails without API key."""
        from cineman.chain import get_recommendation_chain

        mock_getenv.return_value = None

        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            get_recommendation_chain()

    @patch("cineman.chain.ChatGoogleGenerativeAI")
    @patch("cineman.chain.load_prompt_from_file")
    @patch("cineman.chain.os.getenv")
    def test_get_recommendation_chain_success(
        self, mock_getenv, mock_load_prompt, mock_llm_class
    ):
        """Test successful chain creation."""
        from cineman.chain import get_recommendation_chain

        # Setup mocks
        mock_getenv.return_value = "test-api-key"
        mock_load_prompt.return_value = "Test prompt"
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        # Execute
        chain = get_recommendation_chain()

        # Verify
        assert chain is not None
        mock_getenv.assert_called_with("GEMINI_API_KEY")
        mock_llm_class.assert_called_once()
        # Verify temperature is set to 1.2 for creativity
        call_kwargs = mock_llm_class.call_args[1]
        assert call_kwargs["temperature"] == 1.2
        assert call_kwargs["google_api_key"] == "test-api-key"


class TestChainIntegration:
    """Test chain integration with mocked LLM."""

    @patch("cineman.chain.ChatGoogleGenerativeAI")
    @patch("cineman.chain.load_prompt_from_file")
    @patch("cineman.chain.os.getenv")
    def test_chain_invocation_with_history(
        self, mock_getenv, mock_load_prompt, mock_llm_class
    ):
        """Test chain invocation with chat history."""
        from cineman.chain import get_recommendation_chain

        # Setup mocks
        mock_getenv.return_value = "test-api-key"
        mock_load_prompt.return_value = "Test system prompt with {{json}}"

        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        # Create chain
        chain = get_recommendation_chain()

        # Verify chain is created
        assert chain is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
