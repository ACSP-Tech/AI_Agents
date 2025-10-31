import json
import asyncio
import httpx # <-- New: The recommended asynchronous HTTP client for Python
from fastapi import  HTTPException, status
from typing import Dict
from ..sec import API_KEY, API_URL


# --- LLM System Prompt (The Agent's Core Logic) ---
SYSTEM_PROMPT = (
    "You are the 'Momentum Analyst,' a hyper-focused, non-judgmental productivity coach for software developers. "
    "Your core mission is to analyze a user's reported progress (task, time, feeling) and immediately generate "
    "one concrete, tiny, and specific 'Minimum Viable Action' (MVA) they must commit to next. "
    "RULES:\n"
    "1. Never use generic motivational quotes, slogans, or clichés (e.g., 'keep pushing,' 'believe in yourself').\n"
    "2. Be concise, direct, and empathetic. Your analysis must acknowledge their feeling (e.g., 'frustration is a sign of complexity').\n"
    "3. The 'next_minimum_action' MUST be an MVA: a single, simple, measurable step executable in under 15 minutes.\n"
    "4. Base your feedback and action on the intersection of the 'current_focus_area' and the 'feeling' reported.\n"
)

API_TIME_OUT = 30.0

# --- Moderation Configuration ---
BANNED_KEYWORDS = ["kill", "hack", "bomb", "exploit", "violence", "threat"]
MODERATION_FAILURE_MSG = "Your input/output violated the moderation policy."

async def moderate_text(text: str, is_input: bool = True):
    # function to moderate text
    text_lower = text.lower()
    if is_input:
        for keyword in BANNED_KEYWORDS:
            if keyword in text_lower:
                return MODERATION_FAILURE_MSG
        return None
    else:
        moderated_text = text
        for keyword in BANNED_KEYWORDS:
            moderated_text = moderated_text.replace(keyword, "[REDACTED]")
        return moderated_text

async def parse_progress_from_message(client: httpx.AsyncClient, focus_message: str) -> dict:
    """Uses LLM to extract structured data (time, feeling, action) from a single text message."""
    
    # Define a system instruction for the parsing task
    PARSING_PROMPT = (
        "You are a progress report parser. Your task is to extract three fields "
        "from the user's message: 'time_spent_minutes' (convert time phrases like '4 hours' to an integer), "
        "'feeling' (a single, descriptive word like 'frustrated' or 'calm'), "
        "and 'last_action_taken' (a brief description). "
        "If a field cannot be logically deduced from the message, use the following defaults: "
        "time_spent_minutes: 30, feeling: 'Unspecified', last_action_taken: 'N/A'. "
        "Return the result as a strict JSON object matching the provided schema."
    )
    
    # Define the JSON Schema for the extraction output
    parsing_schema = {
        "type": "OBJECT",
        "properties": {
            "time_spent_minutes": {"type": "INTEGER", "description": "Time spent in minutes, calculated from the message."},
            "feeling": {"type": "STRING", "description": "The user's emotional state."},
            "last_action_taken": {"type": "STRING", "description": "The final action taken or last attempt."}
        },
        "required": ["time_spent_minutes", "feeling", "last_action_taken"]
    }
    
    payload = {
        "contents": [{ "parts": [{ "text": f"User message to parse: {focus_message}" }] }],
        "systemInstruction": { "parts": [{ "text": PARSING_PROMPT }] },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": parsing_schema,
            "temperature": 0.0, # Lower temperature for reliable parsing
        },
    }
    try:
        api_response = await call_gemini_api_with_retry(client, payload)
        json_text = api_response.get('candidates')[0]['content']['parts'][0]['text']
        return json.loads(json_text)
    except Exception as e:
        # If parsing fails, return defaults explicitly
        print(f"Parsing LLM failed, using defaults. Error: {e}")
        return {
            "time_spent_minutes": 30,
            "feeling": "Unspecified",
            "last_action_taken": "N/A"
        }

# --- A2A Endpoint Logic ---
async def call_gemini_api_with_retry(client: httpx.AsyncClient, payload: Dict) -> Dict:
    """Handles API call with exponential backoff for resilience using httpx."""
    max_retries = 5
    base_delay = 1.0

    # Use httpx.AsyncClient for asynchronous requests
    for attempt in range(max_retries):
        try:
            response = await client.post(
                API_URL, 
                params={"key": API_KEY},
                headers={'Content-Type': 'application/json'},
                json=payload,
                timeout= API_TIME_OUT
            )
            
            # httpx provides a clean way to raise exceptions on 4xx/5xx status codes
            response.raise_for_status() 
            
            # If successful, return the JSON data
            return response.json()

        except httpx.HTTPStatusError as e:
            # Handles 4xx and 5xx errors from the server.
            status_code = e.response.status_code
            error_detail = f"API returned status {status_code}"
            
            if status_code < 500 or attempt == max_retries - 1:
                # Don't retry client errors (4xx) or if it's the last attempt
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY if status_code >= 500 else status_code,
                    detail=f"Gemini API failed: {error_detail} (Reason: {e.response.text.strip()})"
                )

        except httpx.RequestError as e:
            # Handles network-level errors (timeouts, DNS issues, etc.)
            error_detail = f"Network request failed: {type(e).__name__}"
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Gemini API failed after multiple network retries: {error_detail}"
                )

        # Apply exponential backoff delay before the next retry
        delay = base_delay * (2 ** attempt)
        await asyncio.sleep(delay)