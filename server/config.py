"""
Configuration for Semantic Bit GPU Server
Uses Pydantic Settings for environment variable management
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Server configuration from environment variables"""
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Auto-reload on code changes (dev only)")
    
    # Model settings
    model_id: str = Field(
        default="runwayml/stable-diffusion-v1-5",
        description="HuggingFace model ID"
    )
    device: str = Field(default="cuda", description="Device to run on (cuda/cpu)")
    torch_dtype: str = Field(default="float16", description="Torch dtype (float16/float32)")
    
    # Generation defaults (Codex recommendations)
    default_steps: int = Field(default=28, description="Default inference steps")
    default_guidance_scale: float = Field(default=7.0, description="Default guidance scale")
    default_height: int = Field(default=512, description="Default image height")
    default_width: int = Field(default=512, description="Default image width")
    
    # Scheduler settings
    scheduler_type: str = Field(
        default="DPMSolver++",
        description="Scheduler type (DPMSolver++/EulerAncestral)"
    )
    use_karras_sigmas: bool = Field(default=True, description="Use Karras sigmas for DPMSolver++")
    
    # Performance settings
    offline_mode: bool = Field(default=False, description="Use cached models only (no downloads)")
    local_files_only: bool = Field(default=False, description="HuggingFace local files only")
    
    # API settings
    max_concurrent_requests: int = Field(default=2, description="Max concurrent image generations")
    request_timeout: int = Field(default=60, description="Request timeout in seconds")
    api_key: str | None = Field(default=None, description="Optional API key for Bearer token auth")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
