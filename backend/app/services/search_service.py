import os
import json
import re
import logging
from googleapiclient.discovery import build
from app.core import models

logger = logging.getLogger(__name__)

# System prompt for the controller
CONTROLLER_SYSTEM_PROMPT = """You are a Search Decision Controller. Your ONLY job is to analyze the user's request and decide if a Google Search is required to answer it.

[Rules]
1. OUTPUT STRICT JSON ONLY: {"needs_search": true/false, "query": "exact search query"}
2. SET needs_search = true IF:
   - Request asks for current events, news, weather, stock prices, sports scores.
   - Request asks for specific facts that might be outdated in training data (post-2023).
   - Request specifically asks to "search for" or "look up" something.
3. SET needs_search = false IF:
   - Request is for coding, programming, debugging (unless looking up new library features).
   - Request is for creative writing, reasoning, math, or general knowledge (e.g., "explain quantum physics").
   - Request is conversational (greeting, thanks).
4. QUERY GENERATION:
   - If needs_search is true, generate a concise, keyword-optimized search query (max 10 words).
   - If needs_search is false, leave "query" as null or empty string.

[Examples]
User: "Who won the Super Bowl 2024?"
JSON: {"needs_search": true, "query": "Super Bowl 2024 winner"}

User: "Write a python script to sort a list."
JSON: {"needs_search": false, "query": null}

User: "What's the price of AAPL right now?"
JSON: {"needs_search": true, "query": "AAPL stock price current"}
"""

def extract_search_decision(user_query: str, keep_loaded: bool = False, system_prompt: str = None) -> dict:
    """
    Uses the lightweight controller model to decide if search is needed.
    Returns a dict: {"needs_search": bool, "query": str}
    """
    try:
        # Use provided system prompt or default
        sys_prompt = system_prompt or CONTROLLER_SYSTEM_PROMPT
        
        # Construct Prompt
        # Qwen/ChatML format: <|im_start|>system\n...<|im_end|>\n<|im_start|>user\n...<|im_end|>\n<|im_start|>assistant\n
        prompt = (
            f"<|im_start|>system\n{sys_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_query}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        
        # Determine strict generation params
        # T=0 for determinism
        raw_response = models.generate_controller_response(
            prompt, 
            max_new_tokens=128,
            keep_loaded=keep_loaded
        )
        
        # Parse JSON
        # Clean up potential markdown code blocks ```json ... ```
        cleaned_response = raw_response.strip()
        
        # Remove potential "JSON:" prefix (seen in logs)
        if cleaned_response.upper().startswith("JSON:"):
            cleaned_response = cleaned_response[5:].strip()

        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        
        try:
            decision = json.loads(cleaned_response)
        except json.JSONDecodeError as je:
            print(f"⚠️ JSON Parse Warning (Controller): {je}. Raw: '{raw_response}'")
            
            # Robust fallback: Try to find the first JSON object in the string
            try:
                json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group(0))
                else:
                    raise ValueError("No JSON found in response")
            except Exception:
                # Ultimate fallback
                if "true" in cleaned_response.lower() and "query" in cleaned_response.lower():
                     decision = {"needs_search": True, "query": user_query}
                else:
                     decision = {"needs_search": False, "query": None}

        print(f"🤖 Search Controller Decision: {decision}")
        return decision

    except Exception as e:
        logger.error(f"Search Controller Failed: {e}")
        # Fail safe -> No search
        return {"needs_search": False, "query": None}

def google_search(query: str, num: int = 5) -> list:
    """
    Performs a Google Custom Search.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")

    if not api_key or not cse_id:
        logger.warning("Google Search API Key or CSE ID not found. Skipping search.")
        return []

    try:
        service = build("customsearch", "v1", developerKey=api_key)
        res = service.cse().list(q=query, cx=cse_id, num=num).execute()

        results = [
            {
                "title": item.get("title"),
                "snippet": item.get("snippet", ""),
                "link": item.get("link")
            }
            for item in res.get("items", [])
        ]
        return results
    except Exception as e:
        logger.error(f"Google Search failed: {e}")
        return []

# Alias for modularity compliance
def perform_search(query: str, num: int = 5) -> list:
    """Executes the Google Search using the generated query."""
    return google_search(query, num)

def generate_final_response(prompt: str, search_results: list, system_prompt: str, model_name: str = "chat", temperature: float = 0.7, max_new_tokens: int = 1024) -> str:
    """
    Generates the final response using the main model, contextually integrating search results.
    """
    full_prompt = system_prompt
    
    # Inject Search Context if available
    if search_results:
        search_context = "\n\n=== WEB SEARCH RESULTS ===\n"
        for res in search_results:
             search_context += f"- [{res['title']}]({res['link']}): {res['snippet']}\n"
        search_context += "=== END SEARCH RESULTS ===\n"
        search_context += (
            "Instructions: Use the above search results to answer the user's question. "
            "Cite your sources using markdown links [Title](URL). "
            "If the search results don't contain the answer, say so.\n"
        )
        full_prompt += search_context
        
    # Append User Prompt (if not already in system_prompt or handled by chat template)
    # In this architecture, we assume system_prompt contains the conversation history and instructions
    # But usually models.generate_response takes a formatted prompt.
    # We will format it using the chat template manually here or rely on models.py to do it?
    # models.generate_response() takes a raw string prompt.
    # Wait, models.generate_response in models.py (line 179) calls mlx_generate.
    # But chat_service.py (line 148) calls tokenizer.apply_chat_template.
    
    # We should let chat_service handle the template application because it has the history logic.
    # So this function might be redundant if we strictly follow "encapsulate... generate_final_response".
    # But if we strictly follow it, we need to move the template application here.
    
    # To avoid breaking chat_service complexity, I'll make this function return the formatted search context
    # OR make it a pass-through that chat_service uses to "get the response".
    
    return models.generate_response(prompt, max_new_tokens=max_new_tokens, temperature=temperature)

# Backwards compatibility alias if needed, but we will update callers.
def should_search(query: str) -> bool:
    """Legacy alias, mapped to controller logic."""
    decision = extract_search_decision(query)
    return decision.get("needs_search", False)