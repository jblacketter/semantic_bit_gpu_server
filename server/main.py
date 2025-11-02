"""
Semantic Bit GPU Server - FastAPI Application
Phase 2 Implementation
"""

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from typing import Optional
import logging
from contextlib import asynccontextmanager

from .generator import get_generator
from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Request/Response Models
class GenerateRequest(BaseModel):
    """Image generation request"""
    prompt: str = Field(..., description="Text description of desired image", min_length=1, max_length=1000)
    negative_prompt: Optional[str] = Field(None, description="Things to avoid in the image")
    num_inference_steps: Optional[int] = Field(None, description="Number of denoising steps (20-50 recommended)", ge=1, le=100)
    guidance_scale: Optional[float] = Field(None, description="How closely to follow prompt (5.0-10.0 recommended)", ge=1.0, le=20.0)
    height: Optional[int] = Field(None, description="Image height in pixels (multiple of 8)", ge=256, le=1024)
    width: Optional[int] = Field(None, description="Image width in pixels (multiple of 8)", ge=256, le=1024)
    seed: Optional[int] = Field(None, description="Random seed for reproducibility", ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "a cat sitting on a mat, digital art style, detailed",
                "negative_prompt": "blurry, low quality, distorted",
                "num_inference_steps": 28,
                "guidance_scale": 7.0,
                "seed": 42
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    generator_info: dict


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI app
    Loads model on startup, keeps it warm during runtime
    """
    logger.info("=" * 60)
    logger.info("Semantic Bit GPU Server - Starting")
    logger.info("=" * 60)
    logger.info(f"Model: {settings.model_id}")
    logger.info(f"Device: {settings.device}")
    logger.info(f"Scheduler: {settings.scheduler_type}")
    logger.info(f"Default steps: {settings.default_steps}")
    logger.info(f"Offline mode: {settings.offline_mode}")

    # Load model on startup
    try:
        generator = get_generator()
        generator.load_model()
        logger.info("Model loaded successfully - ready to accept requests")
    except Exception as e:
        logger.error(f"Failed to load model on startup: {e}")
        logger.error("Server will start but generation requests will fail")

    yield  # Server runs here

    logger.info("Shutting down server")


# Create FastAPI app
app = FastAPI(
    title="Semantic Bit GPU Server",
    description="AI Image Generation Microservice for Semantic Bit Theory",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Semantic Bit GPU Server",
        "version": "0.1.0",
        "phase": "Phase 2 - FastAPI Implementation",
        "endpoints": {
            "/generate": "POST - Generate image from prompt",
            "/health": "GET - Health check and system info",
            "/docs": "GET - Interactive API documentation",
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns:
        Server status and generator information
    """
    try:
        generator = get_generator()
        generator_info = generator.get_info()

        return HealthResponse(
            status="healthy",
            model_loaded=generator.model_loaded,
            generator_info=generator_info
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.post("/generate")
async def generate_image(request: GenerateRequest):
    """
    Generate image from text prompt

    Args:
        request: Generation parameters

    Returns:
        PNG image as bytes
    """
    try:
        generator = get_generator()

        if not generator.model_loaded:
            raise HTTPException(
                status_code=503,
                detail="Model not loaded. Server may still be initializing."
            )

        # Generate image
        image_bytes = generator.generate(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            height=request.height,
            width=request.width,
            seed=request.seed,
        )

        # Return image as PNG
        return Response(
            content=image_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": "inline; filename=generated.png"
            }
        )

    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )
