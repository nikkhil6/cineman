from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
import os
import sys

# Helper function to load the prompt content
def load_prompt_from_file(filepath):
    """Reads the prompt text from an external file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Crucial for robust code: raise an error if the config is missing
        raise FileNotFoundError(f"Prompt file not found at: {filepath}")

# Escape braces in system prompt so ChatPromptTemplate doesn't treat JSON braces as template variables.
def escape_braces_for_prompt(text: str) -> str:
    """
    Replace single braces with doubled braces so LangChain's f-string style
    template parsing treats them as literal braces.

    Note: We only apply this to the system prompt text (not the human message template),
    so the human message can still use "{user_input}" as a real variable.
    """
    if not text:
        return text
    return text.replace("{", "{{").replace("}", "}}")

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

    # Load the prompt dynamically from the file
    PROMPT_FILEPATH = "prompts/cineman_system_prompt.txt"
    SYSTEM_PROMPT_CONTENT = load_prompt_from_file(PROMPT_FILEPATH)

    # Escape braces in system prompt so LangChain won't try to interpret JSON braces as variables.
    SAFE_SYSTEM_PROMPT = escape_braces_for_prompt(SYSTEM_PROMPT_CONTENT)

    # 2. Define the Prompt
    # Keep the human template as an actual variable placeholder: "{user_input}"
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SAFE_SYSTEM_PROMPT),
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

    try:
        movie_chain = get_recommendation_chain()
    except Exception as e:
        print(f"FATAL: Failed to load AI Chain: {e}")
        sys.exit(1)

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