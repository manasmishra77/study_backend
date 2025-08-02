from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import cloudinary

from app.core.config import settings
from app.utils.database import create_indexes
from app.routers import auth, users, notes, questions, suggestions, analytics, pdfs  # Add pdfs here

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await create_indexes()
    print("Database indexes created")
    yield
    # Shutdown
    print("Application shutting down")

# Create FastAPI application
app = FastAPI(
    title="Personal Tutor API",
    description="A backend API for a personal tutor application where students can upload handwritten notes, receive feedback, and get personalized question suggestions.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(notes.router)
app.include_router(questions.router)
app.include_router(suggestions.router)
app.include_router(analytics.router)
app.include_router(pdfs.router)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Personal Tutor API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
