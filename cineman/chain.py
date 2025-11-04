from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
import sys

# --- AGENT CONFIGURATION (The Cinephile Persona) ---
SYSTEM_PROMPT = """
You are **The Cinephile**, a highly knowledgeable and enthusiastic AI movie recommendation agent. Your primary function is to save the user time searching by providing one single, outstanding movie recommendation.

**RULES AND FORMAT (CRITICAL):**
1. Maintain an enthusiastic, expert, and conversational tone.
2. Only recommend TWO movies per request.
3. Your response must strictly follow the MANDATORY OUTPUT STRUCTURE below.

**MANDATORY OUTPUT STRUCTURE:**
### 🎬 Your Perfect Match: [Movie Title] ([Year])

**1. The Quick Pitch:**
[A short, 1-2 sentence compelling summary of the movie's plot and vibe.]

**2. Why It Matches Your Request:**
[A brief, targeted explanation of why this movie specifically fits the user's mood, genre, or criteria.]

**3. Award & Prestige Highlight:**
[Mention one to two major, prestigious awards or nominations (e.g., Oscar, Golden Globe, Cannes, BAFTA) the movie received to highlight its quality.]
"""

# --- CORE CHAIN LOGIC ---
def get_recommendation_chain():
    """Builds and returns the stable LangChain Chain for recommendations."""
    
    # CRITICAL FIX: Explicitly retrieve and pass the API key 
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    # 1. Define the LLM (Gemini as the Brain)
    # **FIX:** Pass google_api_key explicitly to bypass Default Credentials Error.
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        temperature=1.0,
        google_api_key=gemini_api_key
    ) 
    
    # 2. Define the Prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "{user_input}"),
        ]
    )
    
    # 3. Define the Output Parser (simply returns the text)
    parser = StrOutputParser()
    
    # 4. Create the Chain: Prompt | LLM | Parser
    chain = prompt | llm | parser
    
    return chain

# --- SAMPLE TEST EXECUTION ---
if __name__ == "__main__":
    
    # Test Setup Check
    if not os.getenv("GEMINI_API_KEY"):
        print("FATAL ERROR: GEMINI_API_KEY environment variable is not set. Please run 'export GEMINI_API_KEY=...' in your terminal.")
        sys.exit(1)

    movie_chain = get_recommendation_chain()

    # Test 1 (Vague mood test for Phase 1 success)
    user_input = "I'm in the mood for a sci-fi movie with a clever plot twist."
    print(f"--- Starting Phase 1 Test ---")
    print(f"User Input: {user_input}\n")
    
    try:
        # Invoke the chain with the user's input
        print("...Calling Gemini API...")
        response = movie_chain.invoke({"user_input": user_input})
        
        print("\n========================================================")
        print("🎬 CINEPHILE'S FINAL RESPONSE (SUCCESSFUL EXECUTION):")
        print(response)
        print("========================================================")

    except Exception as e:
        print(f"FATAL API ERROR during execution: {e}")
        print("Check API Key validity or review your Gemini usage dashboard.")
