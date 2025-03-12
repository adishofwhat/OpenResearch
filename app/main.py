"""
Main FastAPI application for OpenResearch.

This module sets up the FastAPI application, configures logging,
and includes the research routes.
"""

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import routes
from app.routes.research_routes import router as research_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create the FastAPI application
app = FastAPI(
    title="OpenResearch API",
    description="API for the OpenResearch system, providing automated research capabilities",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(research_router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "name": "OpenResearch API",
        "version": "1.0.0",
        "description": "API for automated research using LLMs and web search"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        status_code=200,
        content={"status": "healthy"}
    )

# Error handler for uncaught exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for uncaught exceptions."""
    logger.error(f"Uncaught exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"}
    )

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8000))
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    ) 