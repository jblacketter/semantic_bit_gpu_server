"""
Scheduler Benchmark Script
Compares DPMSolver++ and Euler Ancestral schedulers at different step counts
Per Codex request: Test 20/24/28/32 steps to determine optimal default
"""

import torch
from diffusers import (
    StableDiffusionPipeline,
    DPMSolverMultistepScheduler,
    EulerAncestralDiscreteScheduler,
)
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

MODEL_ID = "runwayml/stable-diffusion-v1-5"
DEVICE = "cuda"
DTYPE = torch.float16

# Test prompts (varied to get good average)
TEST_PROMPTS = [
    "a cat sitting on a mat, digital art style, detailed",
    "a dog running in a yard, watercolor style",
    "a mountain landscape, photorealistic",
]

# Step counts to test (Codex request)
STEP_COUNTS = [20, 24, 28, 32]

# Schedulers to test
SCHEDULERS = {
    "DPMSolver++": lambda config: DPMSolverMultistepScheduler.from_config(
        config,
        algorithm_type="dpmsolver++",
        use_karras_sigmas=True
    ),
    "EulerAncestral": lambda config: EulerAncestralDiscreteScheduler.from_config(config),
}


def benchmark_scheduler(pipe, scheduler_name, scheduler_fn, steps, prompts):
    """
    Benchmark a scheduler with specific step count
    
    Returns:
        Average generation time in seconds
    """
    # Configure scheduler
    pipe.scheduler = scheduler_fn(pipe.scheduler.config)
    
    times = []
    print(f"  Testing {steps} steps...", end=" ", flush=True)
    
    for prompt in prompts:
        start = datetime.now()
        pipe(
            prompt=prompt,
            num_inference_steps=steps,
            guidance_scale=7.0,
            height=512,
            width=512,
        )
        duration = (datetime.now() - start).total_seconds()
        times.append(duration)
    
    avg_time = sum(times) / len(times)
    print(f"{avg_time:.2f}s avg")
    
    return avg_time


def main():
    print("=" * 70)
    print("Scheduler Benchmark - Codex Recommendation Validation")
    print("=" * 70)
    print(f"Model: {MODEL_ID}")
    print(f"Device: {DEVICE}")
    print(f"Test prompts: {len(TEST_PROMPTS)}")
    print(f"Schedulers: {list(SCHEDULERS.keys())}")
    print(f"Step counts: {STEP_COUNTS}")
    print()
    
    # Load pipeline
    print("Loading model...")
    pipe = StableDiffusionPipeline.from_pretrained(
        MODEL_ID,
        torch_dtype=DTYPE,
        local_files_only=True  # Use cached model
    ).to(DEVICE)
    print("Model loaded!\n")
    
    # Results storage
    results = {}
    
    # Test each scheduler
    for scheduler_name, scheduler_fn in SCHEDULERS.items():
        print(f"Testing {scheduler_name}:")
        results[scheduler_name] = {}
        
        for steps in STEP_COUNTS:
            avg_time = benchmark_scheduler(
                pipe, scheduler_name, scheduler_fn, steps, TEST_PROMPTS
            )
            results[scheduler_name][steps] = avg_time
        
        print()
    
    # Print results table
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Scheduler':<20} {' | '.join(f'{s:>6} steps' for s in STEP_COUNTS)}")
    print("-" * 70)
    
    for scheduler_name in SCHEDULERS:
        times_str = " | ".join(
            f"{results[scheduler_name][s]:>7.2f}s" for s in STEP_COUNTS
        )
        print(f"{scheduler_name:<20} {times_str}")
    
    print("=" * 70)
    
    # Find optimal configuration
    print("\nRECOMMENDATIONS:")
    print("-" * 70)
    
    # Find fastest overall
    fastest_time = float('inf')
    fastest_config = None
    
    for scheduler_name in SCHEDULERS:
        for steps in STEP_COUNTS:
            time = results[scheduler_name][steps]
            if time < fastest_time:
                fastest_time = time
                fastest_config = (scheduler_name, steps)
    
    print(f"Fastest: {fastest_config[0]} @ {fastest_config[1]} steps = {fastest_time:.2f}s")
    
    # Codex recommended config
    codex_config = ("DPMSolver++", 28)
    codex_time = results["DPMSolver++"][28]
    print(f"Codex recommended: {codex_config[0]} @ {codex_config[1]} steps = {codex_time:.2f}s")
    
    # Analysis
    print("\nANALYSIS:")
    print("-" * 70)
    
    if fastest_config == codex_config:
        print("✅ Codex recommendation is the fastest configuration!")
    else:
        diff = ((codex_time - fastest_time) / fastest_time) * 100
        print(f"⚠️  Codex config is {diff:+.1f}% slower than fastest")
        print(f"   Trade-off: {codex_config[0]} @ {codex_config[1]} steps may have better quality")
    
    # Quality vs speed trade-off
    print("\nQuality vs Speed:")
    print("- Lower steps (20-24): Faster but may lose detail")
    print("- Medium steps (28): Balanced (Codex recommendation)")
    print("- Higher steps (32): Better quality but slower")
    
    print("\nSuggested defaults based on use case:")
    print(f"  Fast mode: {fastest_config[0]} @ {fastest_config[1]} steps")
    print(f"  Balanced:  DPMSolver++ @ 28 steps (Codex)")
    print(f"  Quality:   DPMSolver++ @ 32 steps")
    
    print("\n" + "=" * 70)
    print("Benchmark complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
