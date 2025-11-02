# Semantic Bit GPU Server

**FastAPI microservice for Stable Diffusion image generation on RTX 4070 Super**

[![Status](https://img.shields.io/badge/status-Phase%202%20Complete-brightgreen)]()
[![Performance](https://img.shields.io/badge/performance-2.06s%20avg-blue)]()
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

Standalone FastAPI microservice that:
- Generates images from text prompts using Stable Diffusion v1.5
- Runs on RTX 4070 Super GPU (WSL2 Ubuntu)
- Provides HTTP REST API for image generation
- **Average generation time: 2.06 seconds** (21% faster than standalone tests)

## 📡 API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Generate Image
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a cat on a mat, digital art"}' \
  --output image.png
```

### API Documentation
```
http://localhost:8000/docs
```

---

## 📊 Performance

**Phase 2 Results** (completed 2025-11-01):

| Metric | Result |
|--------|--------|
| Average generation time | **2.06s** |
| Model load time | ~3s (one-time) |
| Image size | 512x512 PNG |
| Improvement vs Phase 1 | **21.4% faster** |

**Benchmark Details**:
- Image 1: 2.28s (cat on mat)
- Image 2: 1.93s (dog in yard)
- Image 3: 2.00s (mountain landscape)

---

## 🛠️ Tech Stack

- **Framework**: FastAPI 0.120.4
- **Server**: Uvicorn 0.38.0
- **ML Framework**: PyTorch 2.5.1 + CUDA 12.1
- **Model**: Stable Diffusion v1.5 (Hugging Face Diffusers)
- **Scheduler**: DPMSolver++ 2M with Karras sigmas (Codex recommended)
- **GPU**: NVIDIA RTX 4070 Super (12.3GB VRAM)
- **Platform**: WSL2 Ubuntu 24.04 LTS

---

## 📁 Project Structure

```
semantic_bit_gpu_server/
├── server/
│   ├── main.py          # FastAPI app with endpoints
│   ├── generator.py     # Stable Diffusion image generator
│   └── config.py        # Configuration management
├── .env                 # Configuration file (from .env.example)
├── requirements.txt     # Python dependencies
├── run.sh              # Server startup script
└── docs/
    ├── PHASE2_COMPLETE.md       # Phase 2 completion report
    └── README.md                # This file
```

---

## ⚙️ Configuration

Configuration is managed via `.env` file (copy from `.env.example`):

```bash
# Server Settings
HOST=0.0.0.0
PORT=8000

# Model Settings
MODEL_ID=runwayml/stable-diffusion-v1-5
DEVICE=cuda
TORCH_DTYPE=float16

# Generation Defaults (Codex Recommendations)
DEFAULT_STEPS=28
DEFAULT_GUIDANCE_SCALE=7.0
DEFAULT_HEIGHT=512
DEFAULT_WIDTH=512

# Scheduler Settings
SCHEDULER_TYPE=DPMSolver++
USE_KARRAS_SIGMAS=true

# Performance Settings
OFFLINE_MODE=true           # Use cached model (no internet)
LOCAL_FILES_ONLY=true
```

---

## 🔗 Related Repositories

1. **semantic_bit_theory** - Core semantic bit Python package + Gradio demo
   - Location: `~/projects/semantic_bit_theory`
   - Status: Phase 3 Complete (SVG animations working)

2. **newdreamflow** - Django web application (will consume this GPU server)
   - Location: `~/projects/newdreamflow`
   - Status: Ready for integration
   - **Next**: Integrate with GPU server (Phase 3)

---

## 🎓 Architecture

```
┌─────────────────────────────────────────────────┐
│  Django App (newdreamflow)                      │
│  - User interface                               │
│  - HTTP client                                  │
└─────────────────┬───────────────────────────────┘
                  │
                  │ HTTP POST /generate
                  │ {"prompt": "..."}
                  ▼
┌─────────────────────────────────────────────────┐
│  GPU Server (semantic_bit_gpu_server)           │
│  - FastAPI                                      │
│  - Request validation                           │
│  - Image generator                              │
└─────────────────┬───────────────────────────────┘
                  │
                  │ Stable Diffusion
                  │ DPMSolver++ scheduler
                  ▼
┌─────────────────────────────────────────────────┐
│  RTX 4070 Super GPU                             │
│  - CUDA 12.9                                    │
│  - 12.3GB VRAM                                  │
│  - ~2.06s per image                             │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
             PNG image (512x512)
```

---

## 📖 Documentation

- **[Phase 2 Complete](docs/PHASE2_COMPLETE.md)** - Full Phase 2 completion report with benchmarks
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when server running)

---

## ✅ Phase 2 Complete (2025-11-01)

**Completed**:
- [x] FastAPI server with lifecycle management
- [x] `/health` and `/generate` endpoints
- [x] DPMSolver++ scheduler (Codex recommendation)
- [x] Offline mode (cached model)
- [x] Comprehensive logging
- [x] Performance benchmarking (2.06s average)
- [x] Documentation

**Status**: ✅ **READY FOR PHASE 3** (Django Integration)

---

## 🔜 Next Steps - Phase 3

**Goal**: Integrate GPU server with Django newdreamflow app

**Tasks**:
1. Add HTTP client to Django (`requests` library)
2. Create Django views that call GPU server API
3. Implement error handling for server failures
4. Add user-facing image generation feature
5. Test end-to-end Django → GPU Server → Images

**Estimated Time**: 1-2 days

---

## 🚨 Important Notes

1. **Server must be running** for Django to call it
2. **Offline mode enabled** - No internet needed after model cache
3. **Single request at a time** - No queue system yet (add in Phase 3 if needed)
4. **No authentication** - Open API (add security in Phase 3 for production)

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
**Phase**: 2 Complete
**Performance**: 2.06s average (OUTSTANDING)
**Next**: Django Integration (Phase 3)
