import time
import structlog
from typing import Dict, Any, List, Optional, Tuple

from cineman.chain import get_recommendation_chain, build_session_context, format_chat_history
from cineman.validation import validate_movie_list

logger = structlog.get_logger()

class LLMService:
    def __init__(self):
        self.chain = None
        try:
            self.chain = get_recommendation_chain()
            if self.chain:
                logger.info("llm_service_init", message="Movie Recommendation Chain loaded successfully")
            else:
                logger.warning("llm_service_skipped", message="AI Chain skipped (missing API key). App running in degraded mode.")
        except Exception as e:
            logger.error("llm_service_init_failed", message="Failed to load AI Chain", error=str(e))

    def is_available(self) -> bool:
        return self.chain is not None

    def process_chat_request(
        self, 
        user_input: str, 
        chat_history: List[Dict[str, str]], 
        session_id: str
    ) -> Dict[str, Any]:
        """
        Process a chat request: invoke LLM, parse response, validate movies, update history.
        """
        if not self.chain:
             raise RuntimeError("AI service is not available.")

        # 0. Start Timing
        total_start = time.perf_counter()

        # 1. Build Context
        context_start = time.perf_counter()
        # Get previously recommended movies for this session to avoid duplicates
        recommended_movies = self._get_session_recommendations(session_id)
        session_context = build_session_context(chat_history, recommended_movies)
        
        # Format history for LangChain
        langchain_history = format_chat_history(chat_history)
        context_duration = time.perf_counter() - context_start

        # 2. Invoke Chain
        invoke_start = time.perf_counter()
        logger.info("llm_invoke_start", session_id=session_id)
        try:
            # Use the context by appending to user input (invisible to user in chat UI, but visible to LLM)
            # This fixes the bug where context was ignored and avoids double invocation.
            full_input = user_input
            if session_context:
                 full_input += f"\n\n[System Context]: {session_context}"
            
            # Invoke with structured output - SINGLE CALL
            response_obj = self.chain.invoke({
                 "user_input": full_input, 
                 "chat_history": langchain_history
            })
            
            # response_obj is a ChatResponse Pydantic object
            response_text = response_obj.response_text
            raw_movies = [m.model_dump() for m in response_obj.movies]

        except Exception as e:
            logger.error("llm_invoke_failed", error=str(e), session_id=session_id)
            raise e

        invoke_duration = time.perf_counter() - invoke_start
        logger.info("llm_invoke_success", session_id=session_id, duration_s=f"{invoke_duration:.3f}")

        # 3. Validate
        validation_start = time.perf_counter()
        # Pass the raw dicts to validation logic
        # Note: validate_movie_list expects dicts with 'title', 'year', 'director'
        valid_movies, dropped_movies, summary = validate_movie_list(raw_movies, session_id)
        validation_duration = time.perf_counter() - validation_start
        
        # Log dropped
        if dropped_movies:
             logger.info("movies_dropped_validation", count=len(dropped_movies), movies=[m.get('title') for m in dropped_movies])

        total_duration = time.perf_counter() - total_start
        
        # Comprehensive performance log
        logger.info(
            "chat_request_performance",
            total_duration=f"{total_duration:.3f}s",
            context_duration=f"{context_duration:.3f}s",
            llm_duration=f"{invoke_duration:.3f}s",
            validation_duration=f"{validation_duration:.3f}s",
            session_id=session_id
        )

        return {
            "response_text": response_text,
            "movies": valid_movies,
            "validation": {
                **summary,
                "performance": {
                    "total_s": total_duration,
                    "context_s": context_duration,
                    "llm_s": invoke_duration,
                    "validation_s": validation_duration
                }
            }
        }

    def _get_session_recommendations(self, session_id: str) -> List[str]:
        """
        Get list of movies already recommended in this session to avoid duplicates.
        """
        try:
            from cineman.session_manager import get_session_manager
            session_manager = get_session_manager()
            session = session_manager.get_session(session_id)
            if session:
                return session.get_recommended_movies()
            return []
        except Exception as e:
            logger.warning("failed_to_get_session_recommendations", error=str(e), session_id=session_id)
            return []


# Singleton instance
llm_service = LLMService()
