# Momentum Analyst AI (A2A Protocol)

This is a specialized, asynchronous FastAPI agent designed to act as a hyper-focused productivity coach. It receives a user's progress report (which can be a single free-form message) and returns a structured, actionable coaching response, leveraging the Gemini API for natural language generation and parsing.

Crucially, this application implements robust moderation checks on both input and output to ensure policy compliance.

## Key Features

Asynchronous Processing: Uses httpx and asyncio for non-blocking communication with the Gemini API, ensuring high concurrency.

- Two-Step LLM Logic:

    - Parsing: Automatically extracts structured data (time_spent_minutes, feeling, last_action_taken) from a single, unstructured text message using the Gemini API's JSON generation capability.

    - Coaching: Uses the completed structured report to generate a specific Minimum Viable Action (MVA).

    - API Moderation: Implements a keyword-based policy to reject harmful inputs and redact unsafe content in the AI's response.

    - Structured Output: Guarantees responses adhere to the CoachingResponse Pydantic model.

    - Retry Mechanism: Implements exponential backoff to handle transient API errors.

### Prerequisites

    - Python 3.10+

    - pip (Python package installer)

    - Installation and Setup

### Clone the repository and navigate to the project directory.

    - Create a virtual environment and activate it:

        - python -m venv venv
        - source venv/bin/activate  # On Linux/macOS
        - .\venv\Scripts\activate   # On Windows



### Install dependencies:

- pip install fastapi uvicorn httpx pydantic python-decouple
- or pip install -r requirements.txt



### Configure Environment Variables:
Create a file named .env in the root directory and add your Gemini API key and the base API URL:

### .env file content
API_KEY="YOUR_GEMINI_API_KEY_HERE"
API_URL="[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent)"



### Running the Application

- Start the FastAPI server using Uvicorn:

    - uvicorn app.main:app --reload



- The application will be running at http://127.0.0.1:8000. You can view the interactive API documentation at http://127.0.0.1:8000/docs.

### API Endpoint

- POST /a2a/action-accelerator

    - This is the primary endpoint for submitting progress and receiving coaching.

    - Parameter: Required current_focus_area: string, Default for other field

    - Example Request Body (Minimum Input)

        - This is a common use case, where the user just types their issue:

        - {
        -         "current_focus_area": "I'm having trouble with data validation in the Pydantic model. I've been wrestling with it for over two hours and feel really defeated."
        -    }



### Moderation Policy

- The agent implements a simple, keyword-based moderation policy using the BANNED_KEYWORDS list defined in the source code (e.g., ["kill", "hack", "bomb"]).

- Input Moderation: If a banned keyword is found in the current_focus_area, the request is rejected with a 400 BAD REQUEST error and the message: "Your input/output violated the moderation policy."

- Output Moderation: If a banned keyword is generated in the AI's response, it is automatically replaced with [REDACTED] before being returned to the user.