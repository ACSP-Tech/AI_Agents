from pydantic import BaseModel, Field

# --- Pydantic Models for A2A Protocol ---
class ProgressReport(BaseModel):
    """
    The structured input received from the external telex.im platform.
    """
    current_focus_area: str
    time_spent_minutes: int = Field(default=30)
    feeling: str = Field(default="Neutral")
    last_action_taken: str = Field(default="N/A")

class CoachingResponse(BaseModel):
    """
    The structured output sent back to the A2A platform.
    """
    feedback_summary: str
    diagnostic_analysis: str
    next_minimum_action: str

class SingleCoachingReply(BaseModel):
    """
    A unified response model for a single, friendly chat-style reply.
    """
    reply: str