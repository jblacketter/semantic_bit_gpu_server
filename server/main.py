"""
Semantic Bit GPU Server - FastAPI Application
Phase 2 Implementation
"""

from fastapi import FastAPI, HTTPException, Response, Request, Header, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
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
    """
    Image generation request with Codex-recommended bounds

    Bounds enforce safe operation on RTX 4070 Super (12.9GB VRAM):
    - Max resolution 768x768 prevents OOM errors
    - Steps and guidance ranges optimized for quality
    """
    prompt: str = Field(..., description="Text description of desired image", min_length=1, max_length=1000)
    negative_prompt: Optional[str] = Field(None, description="Things to avoid in the image")
    num_inference_steps: int = Field(28, description="Number of denoising steps (5-60)", ge=5, le=60)
    guidance_scale: float = Field(7.0, description="How closely to follow prompt (1.0-12.0)", ge=1.0, le=12.0)
    height: int = Field(512, description="Image height in pixels (256-768, multiple of 8)", ge=256, le=768)
    width: int = Field(512, description="Image width in pixels (256-768, multiple of 8)", ge=256, le=768)
    seed: Optional[int] = Field(None, description="Random seed for reproducibility (0 to 2^32-1)", ge=0, le=2**32-1)
    scheduler: Literal["dpmsolver++", "euler_ancestral"] = Field(
        "dpmsolver++",
        description="Scheduler type (dpmsolver++ recommended by Codex)"
    )

    @field_validator('height', 'width')
    @classmethod
    def check_multiple_of_8(cls, v: int) -> int:
        """Ensure dimensions are multiples of 8 (required by Stable Diffusion)"""
        if v % 8 != 0:
            raise ValueError(f'must be multiple of 8, got {v}')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "a cat sitting on a mat, digital art style, detailed",
                "negative_prompt": "blurry, low quality, distorted",
                "num_inference_steps": 28,
                "guidance_scale": 7.0,
                "seed": 42,
                "scheduler": "dpmsolver++"
            }
        }


class ErrorResponse(BaseModel):
    """Consistent error response format for all non-200 responses"""
    error: str = Field(..., description="Error type (e.g., ValidationError, GenerationFailed)")
    code: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Human-readable error message")
    meta: Optional[dict] = Field(None, description="Additional context (field name, etc.)")


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


# Exception Handlers for Consistent Error Responses
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors with consistent JSON format
    Returns 422 for validation errors (e.g., out of bounds, wrong type)
    """
    # Convert errors to JSON-serializable format
    errors = []
    for error in exc.errors():
        error_dict = {
            "loc": list(error["loc"]),
            "msg": error["msg"],
            "type": error["type"]
        }
        # Add input if present
        if "input" in error:
            error_dict["input"] = str(error["input"])  # Convert to string to ensure serializability
        errors.append(error_dict)

    logger.warning(f"Validation error: {errors}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "code": 422,
            "detail": "Request validation failed",
            "meta": {"errors": errors}
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """
    Handle ValueError (domain-level invalid values)
    Returns 400 for bad requests
    """
    logger.warning(f"ValueError: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "InvalidParameter",
            "code": 400,
            "detail": str(exc),
            "meta": None
        }
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    """
    Handle RuntimeError (generation failures, model errors)
    Returns 500 for internal server errors
    """
    logger.error(f"RuntimeError: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "GenerationFailed",
            "code": 500,
            "detail": str(exc),
            "meta": None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all for unexpected errors
    Returns 500 for internal server errors
    """
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "code": 500,
            "detail": "An unexpected error occurred",
            "meta": {"type": type(exc).__name__}
        }
    )


# API Key Authentication Dependency
async def verify_api_key(authorization: Optional[str] = Header(None)):
    """
    Optional API key verification
    If settings.api_key is None, no authentication required
    If set, requires valid Bearer token
    """
    if settings.api_key is None:
        return  # No auth required

    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization format. Expected: Bearer <token>"
        )

    token = authorization.replace("Bearer ", "")
    if token != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
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


@app.post("/generate", dependencies=[Depends(verify_api_key)])
async def generate_image(request: GenerateRequest):
    """
    Generate image from text prompt with metadata headers

    Args:
        request: Generation parameters

    Returns:
        PNG image as bytes with metadata headers:
        - X-Seed: Actual seed used (for reproducibility)
        - X-Steps: Number of inference steps
        - X-Guidance: Guidance scale value
        - X-Scheduler: Scheduler name
        - X-Device: Device used (cuda/cpu)
        - X-Generation-Time: Elapsed time in seconds
        - Cache-Control: no-store (prevent caching)

    Raises:
        503: Model not loaded
        (Other errors handled by exception handlers)
    """
    import time

    generator = get_generator()

    if not generator.model_loaded:
        return JSONResponse(
            status_code=503,
            content={
                "error": "ServiceUnavailable",
                "code": 503,
                "detail": "Model not loaded. Server may still be initializing.",
                "meta": None
            }
        )

    # Track generation time
    start_time = time.time()

    # Generate image (exception handlers will catch errors)
    image_bytes = generator.generate(
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        num_inference_steps=request.num_inference_steps,
        guidance_scale=request.guidance_scale,
        height=request.height,
        width=request.width,
        seed=request.seed,
        scheduler=request.scheduler,
    )

    elapsed = time.time() - start_time

    # Return image with metadata headers
    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": "inline; filename=generated.png",
            "X-Seed": str(generator.last_seed),
            "X-Steps": str(request.num_inference_steps),
            "X-Guidance": str(request.guidance_scale),
            "X-Scheduler": request.scheduler,
            "X-Device": generator.device,
            "X-Generation-Time": f"{elapsed:.2f}s",
            "Cache-Control": "no-store"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )
