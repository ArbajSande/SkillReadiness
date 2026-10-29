import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import db_manager
from app.routes import health, auth, resume, assessment, readiness, learning_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("skillreadiness.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce production security constraints
    settings.validate_production_security()
    # Startup: connect to MongoDB
    logger.info("Initializing SkillReadiness AI Backend...")
    await db_manager.connect()
    yield
    # Shutdown: close connections
    logger.info("Shutting down SkillReadiness AI Backend...")
    await db_manager.disconnect()

app = FastAPI(
    title="SkillReadiness AI API",
    description="Intelligent Skill Extraction, Readiness Assessment, and Dynamic Learning Path Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins in local dev/testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(assessment.router)
app.include_router(readiness.router)
app.include_router(learning_path.router)

@app.get("/")
async def root():
    return {
        "project": "SkillReadiness AI",
        "status": "online",
        "documentation": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
