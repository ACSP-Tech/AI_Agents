from fastapi import FastAPI
from .setup_main import configure_cors
from .router import momentum
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        print("Application Shutdown: Cleanup complete.")

# --- FastAPI Setup ---
app = FastAPI(
    title="Momentum Analyst AI (A2A Protocol)",
    description="A highly specific, action-oriented motivational agent that analyzes progress reports via A2A protocol and generates personalized coaching using the Gemini API.",
    lifespan=lifespan
)

#defining CORS middleware
configure_cors(app)


app.include_router(momentum.router)


