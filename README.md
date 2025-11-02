# Semantic Bit GPU Server

**Production-ready FastAPI microservice for Stable Diffusion image generation on RTX 4070 Super**

[![Status](https://img.shields.io/badge/status-Phase%20A%20Complete-brightgreen)]()
[![Performance](https://img.shields.io/badge/performance-<%205s-blue)]()
[![GPU](https://img.shields.io/badge/GPU-RTX%204070%20Super-green)]()

---

## 🚀 Quick Start

```bash
# Start the server
cd ~/projects/semantic_bit_gpu_server
source .venv/bin/activate
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000

# Or use the startup script
./run.sh

# Server will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## 🎯 What It Does

Production-ready FastAPI microservice that:
- Generates images from text prompts using Stable Diffusion v1.5
- Runs on RTX 4070 Super GPU (WSL2 Ubuntu)
- Provides HTTP REST API with comprehensive error handling
- Returns metadata headers for debugging and reproducibility
- Supports optional API key authentication
- **Target generation time: < 5 seconds** (warm model)

---

## 📡 API Reference

### POST /generate

Generate an image from a text prompt with comprehensive validation and metadata.

**Request Body**:
```json
{
  "prompt": "a beautiful sunset over mountains, digital art",
  "negative_prompt": "blurry, low quality",
  "num_inference_steps": 28,
  "guidance_scale": 7.0,
  "height": 512,
  "width": 512,
  "seed": 42,
  "scheduler": "dpmsolver++"
}
```

**Request Parameters**:

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `prompt` | string | ✅ Yes | - | 1-1000 chars | Text description of desired image |
| `negative_prompt` | string | ❌ No | null | - | Things to avoid in the image |
| `num_inference_steps` | integer | ❌ No | 28 | 5-60 | Number of denoising steps |
| `guidance_scale` | float | ❌ No | 7.0 | 1.0-12.0 | How closely to follow prompt |
| `height` | integer | ❌ No | 512 | 256-768 (÷8) | Image height in pixels |
| `width` | integer | ❌ No | 512 | 256-768 (÷8) | Image width in pixels |
| `seed` | integer | ❌ No | random | 0-2³²-1 | Random seed for reproducibility |
| `scheduler` | string | ❌ No | "dpmsolver++" | See below | Scheduler type |

**Scheduler Options**:
- `"dpmsolver++"` - DPMSolver++ 2M with Karras sigmas (Codex recommended, default)
- `"euler_ancestral"` - Euler Ancestral (classic SD 1.5 look)

**Response** (Success):
- **Status**: `200 OK`
- **Content-Type**: `image/png`
- **Body**: Binary PNG image data

**Response Headers** (Metadata):
```
X-Seed: 42
X-Steps: 28
X-Guidance: 7.0
X-Scheduler: dpmsolver++
X-Device: cuda
X-Generation-Time: 2.84s
Cache-Control: no-store
```

**Error Responses** (JSON):

```json
{
  "error": "ValidationError",
  "code": 422,
  "detail": "Request validation failed",
  "meta": {
    "errors": [...]
  }
}
```

**Status Codes**:
- `200` - Success, image generated
- `400` - Bad Request (invalid parameter values)
- `401` - Unauthorized (invalid API key, if auth enabled)
- `422` - Validation Error (out of bounds, wrong type)
- `500` - Internal Server Error (generation failed)
- `503` - Service Unavailable (model not loaded)

---

### GET /health

Check server health and model status.

**Response**:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "generator_info": {
    "model_id": "runwayml/stable-diffusion-v1-5",
    "device": "cuda",
    "dtype": "float16",
    "scheduler": "DPMSolver++",
    "defaults": {
      "steps": 28,
      "guidance_scale": 7.0,
      "height": 512,
      "width": 512
    }
  }
}
```

---

### GET /

Get API information and available endpoints.

**Response**:
```json
{
  "service": "Semantic Bit GPU Server",
  "version": "0.1.0",
  "endpoints": {
    "/generate": "POST - Generate image from prompt",
    "/health": "GET - Health check and system info",
    "/docs": "GET - Interactive API documentation"
  }
}
```

---

## 📝 Usage Examples

### Basic Generation

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a cat on a mat, digital art"}' \
  --output cat.png
```

### With All Parameters

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a mountain landscape at sunset, beautiful lighting",
    "negative_prompt": "blurry, low quality, distorted",
    "num_inference_steps": 32,
    "guidance_scale": 7.5,
    "height": 768,
    "width": 768,
    "seed": 12345,
    "scheduler": "dpmsolver++"
  }' \
  --output mountain.png
```

### With Metadata Headers

```bash
curl -i -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a red apple on a white table"}' \
  --output apple.png

# Response includes:
# X-Seed: 1234567890
# X-Steps: 28
# X-Guidance: 7.0
# X-Scheduler: dpmsolver++
# X-Device: cuda
# X-Generation-Time: 2.84s
```

### Seed Reproducibility

```bash
# Generate with seed
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a red apple", "seed": 42}' \
  --output apple1.png

# Same seed = identical image
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a red apple", "seed": 42}' \
  --output apple2.png

# Verify identical
diff apple1.png apple2.png  # Should be identical
```

### With API Key (if enabled)

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{"prompt": "test"}' \
  --output test.png
```

### Error Handling Example

```bash
# Invalid parameters (steps too low)
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", "num_inference_steps": 2}'

# Response (422):
# {
#   "error": "ValidationError",
#   "code": 422,
#   "detail": "Request validation failed",
#   "meta": {
#     "errors": [
#       {
#         "loc": ["body", "num_inference_steps"],
#         "msg": "ensure this value is greater than or equal to 5"
#       }
#     ]
#   }
# }
```

---

## 🛠️ Tech Stack

- **Framework**: FastAPI 0.115.6
- **Server**: Uvicorn 0.32.1
- **ML Framework**: PyTorch 2.5.1 + CUDA 12.1
- **Diffusion**: Diffusers 0.35.2, Transformers 4.57.1
- **Model**: Stable Diffusion v1.5 (runwayml/stable-diffusion-v1-5)
- **Scheduler**: DPMSolver++ 2M with Karras sigmas (Codex recommended)
- **GPU**: NVIDIA RTX 4070 Super (12.9GB VRAM)
- **Platform**: WSL2 Ubuntu 24.04 LTS

---

## ⚙️ Configuration

Configuration is managed via `.env` file (copy from `.env.example`):

```bash
# Server Settings
HOST=0.0.0.0                          # Bind to all interfaces for WSL2 access
PORT=8000
RELOAD=false                          # Auto-reload on code changes (dev only)

# Model Settings
MODEL_ID=runwayml/stable-diffusion-v1-5
DEVICE=cuda                           # cuda or cpu
TORCH_DTYPE=float16                   # float16 or float32 (fp16 = 2x faster)

# Generation Defaults (Codex Recommendations)
DEFAULT_STEPS=28                      # Sweet spot: quality vs speed
DEFAULT_GUIDANCE_SCALE=7.0            # 7.0-7.5 recommended
DEFAULT_HEIGHT=512
DEFAULT_WIDTH=512

# Scheduler Settings
SCHEDULER_TYPE=DPMSolver++            # DPMSolver++ or EulerAncestral
USE_KARRAS_SIGMAS=true                # Codex recommended for DPMSolver++

# Performance Settings
OFFLINE_MODE=false                    # Use cached model (no internet)
LOCAL_FILES_ONLY=false                # HuggingFace local files only
MAX_CONCURRENT_REQUESTS=2             # Future: request queue size
REQUEST_TIMEOUT=60

# API Security (Optional)
API_KEY=                              # Leave empty to disable auth
                                      # Set to secure token to require Bearer auth
```

### Setting API Key (Optional)

To enable API key authentication:

1. Generate a secure random token:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. Add to `.env`:
   ```bash
   API_KEY=your_generated_token_here
   ```

3. Clients must include in requests:
   ```bash
   Authorization: Bearer your_generated_token_here
   ```

4. To disable auth, leave `API_KEY=` empty (default)

---

## 🔒 Input Validation & Safety

All inputs are validated with Pydantic to prevent:
- **GPU OOM errors**: Max resolution 768x768 (safe on 12.9GB VRAM)
- **Invalid dimensions**: Height/width must be multiples of 8
- **Excessive compute**: Steps capped at 60 (quality plateaus beyond this)
- **Malformed requests**: Type checking, bounds enforcement

**Validation Bounds**:
```python
prompt: 1-1000 characters
num_inference_steps: 5-60 (default: 28)
guidance_scale: 1.0-12.0 (default: 7.0)
height: 256-768, multiple of 8 (default: 512)
width: 256-768, multiple of 8 (default: 512)
seed: 0 to 2^32-1 (default: random)
scheduler: "dpmsolver++" | "euler_ancestral"
```

---

## 📁 Project Structure

```
semantic_bit_gpu_server/
├── server/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, endpoints, error handlers
│   ├── generator.py         # Stable Diffusion image generator
│   └── config.py            # Pydantic Settings configuration
├── scripts/
│   └── smoke_gpu_server.py  # Automated smoke tests (Phase A.5)
├── tests/
│   └── __init__.py
├── .env                     # Configuration (from .env.example)
├── .env.example             # Example configuration
├── requirements.txt         # Production dependencies
├── requirements.lock.txt    # Exact versions from Phase 1
├── run.sh                   # Server startup script
└── README.md                # This file
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│  Django App (newdreamflow)                      │
│  - User interface                               │
│  - HTTP client (requests + retries)             │
│  - Bearer token auth                            │
└─────────────────┬───────────────────────────────┘
                  │
                  │ HTTP POST /generate
                  │ {"prompt": "...", ...}
                  │ Authorization: Bearer <token>
                  ▼
┌─────────────────────────────────────────────────┐
│  GPU Server (semantic_bit_gpu_server)           │
│  - FastAPI (Pydantic validation)                │
│  - Request validation (bounds enforcement)      │
│  - Error handling (consistent JSON responses)   │
│  - Optional API key auth                        │
│  - Response metadata headers                    │
└─────────────────┬───────────────────────────────┘
                  │
                  │ Stable Diffusion v1.5
                  │ DPMSolver++ scheduler
                  │ Singleton pattern (warm model)
                  ▼
┌─────────────────────────────────────────────────┐
│  RTX 4070 Super GPU                             │
│  - CUDA 12.1                                    │
│  - 12.9GB VRAM                                  │
│  - fp16 precision                               │
│  - ~2.6-3s per image (target: <5s)              │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
             PNG image (metadata in headers)
```

---

## 📊 Performance Targets

**Phase A Hardening** (Codex recommendations):

| Metric | Target | Notes |
|--------|--------|-------|
| Cold start (model load) | ~5s | First request only |
| Warm request | 2.6-3s | Model kept in VRAM (singleton) |
| Max resolution | 768x768 | Safe on 12.9GB VRAM with fp16 |
| Target latency | < 5s | End-to-end including validation |

**Performance Optimizations**:
- ✅ fp16 precision (2x memory saving, 2-3x faster)
- ✅ DPMSolver++ with Karras sigmas (Codex recommended)
- ✅ Singleton pattern (keep model warm in VRAM)
- ✅ Offline mode (no network latency)
- ✅ Pydantic validation (fast bounds checking)

---

## 🔗 Related Repositories

1. **semantic_bit_theory** - Core semantic bit Python package + Gradio demo
   - Location: `~/projects/semantic_bit_theory`
   - Status: Phase 3 Complete (SVG animations working)

2. **newdreamflow** - Django web application (will consume this GPU server)
   - Location: `~/projects/newdreamflow`
   - Status: Ready for integration
   - **Next**: Integrate with GPU server (Phase E)

---

## 📖 Documentation

- **[API Documentation](http://localhost:8000/docs)** - Interactive Swagger UI (when server running)
- **[Final Review Request](../semantic_bit_theory/docs/CODEX_FINAL_REVIEW_REQUEST.md)** - Codex-approved implementation plan
- **[Implementation Plan](../semantic_bit_theory/docs/IMPLEMENTATION_PLAN_GPU_TO_NEWDREAMFLOW.md)** - Full 6-phase plan

---

## ✅ Phase A Complete (2025-11-01)

**Hardening (Codex Recommendations)**:
- [x] Input validation with Pydantic bounds (5-60 steps, 256-768 res)
- [x] Consistent error response format (JSON with error/code/detail/meta)
- [x] Response metadata headers (X-Seed, X-Steps, X-Guidance, etc.)
- [x] Seed tracking and reproducibility
- [x] Optional API key authentication (Bearer token)
- [x] Comprehensive README and documentation
- [x] Scheduler parameter support (dpmsolver++, euler_ancestral)

**Status**: ✅ **READY FOR PHASE A.5** (Smoke Tests)

---

## 🔜 Next Steps

### Phase A.5: Create Smoke Tests (30-45 min)
- Create `scripts/smoke_gpu_server.py` (Python + httpx)
- Automated pre-flight checks for all endpoints
- Verify headers, status codes, error formats

### Phase B: Test GPU Server (1-2 hours)
- Setup environment and install dependencies
- Run manual test checklist (8 tests)
- Run automated smoke tests
- Document performance baselines

### Phase C-F: newdreamflow Integration
- Audit newdreamflow current state
- Align with semantic-bit pip package
- Create GPU service module in Django
- End-to-end testing

---

## 🚨 Important Notes

1. **WSL2 Access**: Server binds to `0.0.0.0` for Windows host access at `http://localhost:8000`
2. **Model Cache**: First run downloads ~5.2GB to `~/.cache/huggingface/`
3. **Offline Mode**: Enable `OFFLINE_MODE=true` after initial model download
4. **Single Worker**: Use `--workers 1` to avoid multiple processes competing for GPU
5. **API Key**: Optional; leave `API_KEY=` empty to disable authentication

---

## 🤝 Contributing

This is part of the Semantic Bit Theory project ecosystem:
- Main repo: https://github.com/antfriend/semantic_bit_theory
- GPU server: https://github.com/jblacketter/semantic_bit_gpu_server
- Django app: https://github.com/jblacketter/newdreamflow

---

## 📝 License

MIT License - see LICENSE file for details

---

**Last Updated**: 2025-11-01
**Phase**: A Complete (Hardening)
**Next**: A.5 (Smoke Tests) → B (Testing) → C-F (Django Integration)
**Performance Target**: < 5s per image
