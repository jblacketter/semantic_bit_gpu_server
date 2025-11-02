"""
Stable Diffusion Image Generator
Implements Codex-recommended DPMSolver++ scheduler with Karras sigmas
"""

import torch
from diffusers import (
    StableDiffusionPipeline,
    DPMSolverMultistepScheduler,
    EulerAncestralDiscreteScheduler,
)
from typing import Optional, Literal
import logging
from pathlib import Path

from .config import settings

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Stable Diffusion image generator with optimized settings"""

    def __init__(self):
        self.pipe = None
        self.device = settings.device
        self.model_loaded = False
        self.last_seed = None  # Track last used seed for response headers
        
    def load_model(self) -> None:
        """
        Load Stable Diffusion model with recommended settings
        
        Uses:
        - float16 for GPU efficiency (2x memory saving, 2-3x faster)
        - DPMSolver++ 2M with Karras sigmas (Codex recommendation)
        - Keeps model in VRAM between requests (warm cache)
        """
        if self.model_loaded:
            logger.info("Model already loaded, skipping...")
            return
            
        logger.info(f"Loading model: {settings.model_id}")
        logger.info(f"Device: {self.device}, dtype: {settings.torch_dtype}")
        
        # Determine torch dtype
        dtype = torch.float16 if settings.torch_dtype == "float16" else torch.float32
        
        # Load pipeline
        load_kwargs = {
            "torch_dtype": dtype,
        }
        
        if settings.offline_mode or settings.local_files_only:
            load_kwargs["local_files_only"] = True
            logger.info("Offline mode: Using cached model only")
        
        try:
            self.pipe = StableDiffusionPipeline.from_pretrained(
                settings.model_id,
                **load_kwargs
            )
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
        
        # Move to GPU
        self.pipe = self.pipe.to(self.device)
        
        # Set scheduler (Codex recommendation: DPMSolver++ 2M with Karras)
        self._configure_scheduler(settings.scheduler_type)
        
        self.model_loaded = True
        logger.info("Model loaded successfully and moved to GPU")
        logger.info(f"Scheduler: {settings.scheduler_type}")
        
    def _configure_scheduler(
        self,
        scheduler_type: Literal["DPMSolver++", "EulerAncestral", "dpmsolver++", "euler_ancestral"] = "DPMSolver++"
    ) -> None:
        """
        Configure the diffusion scheduler

        Args:
            scheduler_type: Type of scheduler to use (case-insensitive)
                - "dpmsolver++" or "DPMSolver++": DPMSolver++ 2M with Karras sigmas (default, Codex recommended)
                - "euler_ancestral" or "EulerAncestral": Euler Ancestral (classic SD 1.5 look)
        """
        # Normalize to lowercase for comparison
        scheduler_lower = scheduler_type.lower()

        if scheduler_lower == "dpmsolver++":
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipe.scheduler.config,
                algorithm_type="dpmsolver++",
                use_karras_sigmas=settings.use_karras_sigmas
            )
            logger.info("Configured DPMSolver++ 2M scheduler with Karras sigmas")

        elif scheduler_lower == "euler_ancestral" or scheduler_lower == "eulerancestral":
            self.pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(
                self.pipe.scheduler.config
            )
            logger.info("Configured Euler Ancestral scheduler")

        else:
            raise ValueError(f"Unknown scheduler type: {scheduler_type}")
    
    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        height: Optional[int] = None,
        width: Optional[int] = None,
        seed: Optional[int] = None,
        scheduler: Optional[Literal["dpmsolver++", "euler_ancestral"]] = None,
    ) -> bytes:
        """
        Generate image from prompt

        Args:
            prompt: Text description of desired image
            negative_prompt: Things to avoid in the image
            num_inference_steps: Number of denoising steps (default: 28 from Codex)
            guidance_scale: How closely to follow prompt (default: 7.0 from Codex)
            height: Image height in pixels (default: 512)
            width: Image width in pixels (default: 512)
            seed: Random seed for reproducibility (auto-generated if None)
            scheduler: Scheduler type (dpmsolver++ or euler_ancestral)

        Returns:
            Image as PNG bytes
        """
        if not self.model_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Use defaults from config if not specified
        num_inference_steps = num_inference_steps or settings.default_steps
        guidance_scale = guidance_scale or settings.default_guidance_scale
        height = height or settings.default_height
        width = width or settings.default_width

        # Generate seed if not provided
        if seed is None:
            import random
            seed = random.randint(0, 2**32 - 1)

        # Track seed for response headers
        self.last_seed = seed

        # Configure scheduler if specified
        if scheduler is not None:
            self._configure_scheduler(scheduler)

        logger.info(f"Generating image: prompt='{prompt[:50]}...', steps={num_inference_steps}, guidance={guidance_scale}, seed={seed}")

        # Create generator with seed
        generator = torch.Generator(device=self.device).manual_seed(seed)
        
        # Generate image
        result = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            height=height,
            width=width,
            generator=generator,
        )
        
        image = result.images[0]
        
        # Convert to PNG bytes
        from io import BytesIO
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        
        logger.info(f"Image generated successfully ({len(image_bytes)} bytes)")
        return image_bytes
    
    def get_info(self) -> dict:
        """Get generator information and status"""
        return {
            "model_id": settings.model_id,
            "device": self.device,
            "dtype": settings.torch_dtype,
            "scheduler": settings.scheduler_type,
            "model_loaded": self.model_loaded,
            "defaults": {
                "steps": settings.default_steps,
                "guidance_scale": settings.default_guidance_scale,
                "height": settings.default_height,
                "width": settings.default_width,
            }
        }


# Global generator instance (singleton pattern - keep model warm)
_generator: Optional[ImageGenerator] = None


def get_generator() -> ImageGenerator:
    """Get or create the global generator instance"""
    global _generator
    if _generator is None:
        _generator = ImageGenerator()
    return _generator
