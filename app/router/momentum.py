from fastapi import APIRouter
import textwrap
from ..schema.momentum import SingleCoachingReply, ProgressReport
import json
import httpx
from fastapi import HTTPException, status
from ..utils.momentum import SYSTEM_PROMPT, moderate_text, parse_progress_from_message, call_gemini_api_with_retry


router = APIRouter(tags=["A2A Coaching"])

@router.post(
    "/a2a/action-accelerator", 
    response_model=SingleCoachingReply,
    status_code=status.HTTP_201_CREATED
)
async def accelerate_action(report: ProgressReport):
    """
    Q: Motivational A2A Protocol Agent
    Receives a progress report and returns structured, actionable coaching.
    """
    # --- 1. Input Moderation Check ---
    input_text = report.current_focus_area # Only moderate the user's message
    input_moderation_result = await moderate_text(input_text, is_input=True)
    if input_moderation_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=input_moderation_result
        )
    async with httpx.AsyncClient() as client:
        try:

            # Check if the client provided a complete report or just a message
            parsed_data = await parse_progress_from_message(client, report.current_focus_area)
            
            # Update the report object with the deduced data
            report.time_spent_minutes = parsed_data.get("time_spent_minutes", 30)
            report.feeling = parsed_data.get("feeling", "Unspecified")
            report.last_action_taken = parsed_data.get("last_action_taken", "N/A")

            # Construct the user query for the LLM
            user_query = (
                f"Analyze this progress report: "
                f"Focus: {report.current_focus_area}. "
                f"Time Spent: {report.time_spent_minutes} minutes. "
                f"Current Feeling: {report.feeling}. "
                f"Last Action: {report.last_action_taken}. "
                f"Generate the required structured coaching response based on the SYSTEM_PROMPT."
            )

            #Define the desired structured response format (JSON Schema)
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "feedback_summary": {"type": "STRING", "description": "A brief, direct summary of the situation."},
                    "diagnostic_analysis": {"type": "STRING", "description": "A concise, non-cliché analysis of the user's current feeling/block."},
                    "next_minimum_action": {"type": "STRING", "description": "The MVA (Minimum Viable Action) the user must do next (15 min max)."}
                },
                "propertyOrdering": ["feedback_summary", "diagnostic_analysis", "next_minimum_action"]
            }

            #Construct the API Payload
            payload = {
                "contents": [{ "parts": [{ "text": user_query }] }],
                "systemInstruction": { "parts": [{ "text": SYSTEM_PROMPT }] },
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": response_schema
                },
            }

            # Call the Gemini API
            api_response = {} # Initialize in case of error
   
            api_response = await call_gemini_api_with_retry(client, payload)
            
            # Extract and Parse the JSON content
            # Note: LLM JSON responses come back as a string nested inside the 'text' key
            json_text = api_response.get('candidates')[0]['content']['parts'][0]['text']
            coaching_data = json.loads(json_text)

            #Output Moderation Check and Redaction ---
            summary = await moderate_text(coaching_data.get('feedback_summary', ''), is_input=False)
            analysis = await moderate_text(coaching_data.get('diagnostic_analysis', ''), is_input=False)
            action = await moderate_text(coaching_data.get('next_minimum_action', ''), is_input=False)
            
            final_reply = textwrap.dedent(
                f"""\
            Minimum Action (MVA)
            Your single, smallest next step is: {action}"""
            )

            # 5. Validate and return the structured response
            return SingleCoachingReply(reply=final_reply)

        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
            # Catch issues if the LLM response structure is unexpected or JSON parsing fails
            # Raise an internal server error with details for debugging
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to parse LLM response: {str(e)} - Raw Response: {json.dumps(api_response, indent=2)}"
            )
        except HTTPException:
            # Re-raise the HTTPException thrown by call_gemini_api_with_retry
            raise
        except Exception as e:
            # Catch any other unexpected exceptions
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred: {str(e)}"
            )