# MediScope LlamaIndex AI Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Production-ready medical voice + vision AI agent with FastAPI backend and responsive frontend. Includes modular services for RAG, STT, TTS, OCR, and optional medical vision model usage.

## ⚠️ Important Medical Disclaimer

**This system is for education and triage support only.**  
It must NOT be used for:
- Medical diagnosis
- Prescribing treatments or medications  
- Replacing professional medical advice
- Emergency medical situations

Always consult qualified healthcare professionals for medical decisions.

## ✨ Key Features

- **🎯 Production-Ready**: Comprehensive error handling, logging, and monitoring
- **🔧 Modular Architecture**: Pluggable providers for LLM, RAG, STT, TTS, and vision
- **🏠 Local AI Support**: Run medical models locally with LM Studio (no API costs!)
- **🔒 Safety Guardrails**: Red-flag detection with emergency escalation notices
- **📚 RAG Support**: LlamaIndex integration with simple fallback
- **🎤 Voice Pipeline**: Speech-to-text and text-to-speech capabilities
- **👁️ Vision Analysis**: OCR and medical vision model support (Mini-InternVL2-1B-DA-Medical)
- **🐳 Docker Ready**: Docker and docker-compose for easy deployment
- **📊 Comprehensive Logging**: Structured logging with rotation and error tracking
- **♻️ Retry Logic**: Automatic retry with exponential backoff for external services
- **✅ Input Validation**: Robust validation for all user inputs

## 🏗️ Architecture

```
mediscope/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes with error handling
│   │   ├── core/         # Configuration, logging, exceptions
│   │   ├── schemas/      # Pydantic models
│   │   └── services/     # Business logic with retry and validation
│   ├── requirements.txt  # Core dependencies
│   └── requirements-ml.txt  # ML/AI dependencies
├── frontend/            # HTML/CSS/JS interface
├── data/               # RAG store and documents
├── logs/              # Application logs
├── Dockerfile
├── docker-compose.yml
└── .env.example       # Configuration template
```

## 🚀 Quick Start

### Local Development

1. **Clone and setup:**
   ```bash
   cd "E:\Data Science\ML_and_DL_project\NLP Project\MediScope LlamaIndex AI Agent"
   cd backend
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   # source .venv/bin/activate  # On Linux/Mac
   ```

2. **Install dependencies:**
   ```bash
   # Core dependencies
   pip install -r requirements.txt
   
   # Optional: ML dependencies (LlamaIndex, OCR, STT/TTS, VLM)
   pip install -r requirements-ml.txt
   ```

3. **Configure environment:**
   ```bash
   copy ..\.env.example ..\.env  # Windows
   # cp ../.env.example ../.env  # Linux/Mac
   
   # Edit .env with your configuration
   ```

4. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the UI:**
   - Open http://localhost:8000/ in your browser
   - API docs: http://localhost:8000/docs

### Docker Deployment

```bash
# Build and start services
docker-compose up --build

# Access at http://localhost:8000/
```

## 🏥 LM Studio + Medical Models (NEW!)

MediScope now supports **local medical AI** using:
- **LM Studio** with **qwen3-medical-gguf** for medical text generation
- **Mini-InternVL2-1B-DA-Medical** for medical image analysis

### Why Use LM Studio?

✅ **100% Privacy**: All data stays on your machine  
✅ **No Costs**: No API fees  
✅ **Medical Specialized**: Models trained for medical use  
✅ **Offline Ready**: Works without internet (after setup)  
✅ **HIPAA-Friendly**: Complete data control  

### Quick Setup

1. **Download LM Studio**: https://lmstudio.ai/
2. **Install and load model**: `towardsinnovationlab/qwen3-medical-gguf`
3. **Start local server** (port 1234)
4. **Configure MediScope**:
   ```bash
   # Copy the LM Studio configuration template
   copy .env.lmstudio.example .env
   
   # Or manually edit .env:
   LLM_PROVIDER=lmstudio
   LLM_MODEL=towardsinnovationlab/qwen3-medical-gguf
   LMSTUDIO_URL=http://localhost:1234
   
   VISION_PROVIDER=internvl
   VISION_MODEL=OpenGVLab/Mini-InternVL2-1B-DA-Medical
   ```

5. **Install vision dependencies**:
   ```bash
   pip install transformers torch torchvision accelerate
   ```

6. **Run MediScope**:
   ```bash
   run.bat
   ```

### Detailed Guides

- **📘 English Setup Guide**: See [LMSTUDIO_SETUP.md](LMSTUDIO_SETUP.md)
- **📗 Bengali Setup Guide (বাংলা)**: See [LMSTUDIO_SETUP_BANGLA.md](LMSTUDIO_SETUP_BANGLA.md)
- **📙 Integration Details**: See [LMSTUDIO_INTEGRATION.md](LMSTUDIO_INTEGRATION.md)

### System Requirements

**Minimum:**
- RAM: 8 GB
- Storage: 10 GB free
- OS: Windows 10/11, macOS, Linux

**Recommended:**
- RAM: 16 GB+
- Storage: 20 GB+
- GPU: NVIDIA GPU with 6GB+ VRAM (optional, for faster inference)

## 📋 Configuration

### Environment Variables

See `.env.example` for all available options. Key settings:

```bash
# Application
ENVIRONMENT=local  # local, development, staging, production
LOG_LEVEL=INFO     # DEBUG, INFO, WARNING, ERROR, CRITICAL
DEMO_MODE=true     # Enable demo responses

# Providers
LLM_PROVIDER=none     # none, openai, vllm, lmstudio
RAG_PROVIDER=simple   # simple, llamaindex
STT_PROVIDER=none     # none, faster_whisper, openai
TTS_PROVIDER=none     # none, gtts, coqui
VISION_PROVIDER=none  # none, internvl, vllm
OCR_PROVIDER=none     # none, tesseract

# API Keys and URLs
OPENAI_API_KEY=your-key-here
LMSTUDIO_URL=http://localhost:1234  # For LM Studio
```

### Provider Selection Guide

**LLM Providers:**
- `none`: Demo mode with hardcoded responses
- `openai`: OpenAI GPT models (requires API key, costs money)
- `vllm`: Self-hosted vLLM server (requires GPU server setup)
- `lmstudio`: LM Studio local server (free, private, runs locally) **← NEW!**

**RAG Providers:**
- `simple`: JSON-based keyword matching (no dependencies)
- `llamaindex`: Vector store with embeddings (requires llama-index)

**STT Providers:**
- `none`: Disabled
- `faster_whisper`: Local Whisper model (requires faster-whisper)
- `openai`: OpenAI Whisper API (requires API key)

**TTS Providers:**
- `none`: Disabled
- `gtts`: Google Text-to-Speech (requires gTTS)
- `coqui`: Coqui TTS models (requires TTS)

**Vision Providers:**
- `none`: OCR only
- `internvl`: Medical vision model from HuggingFace (Mini-InternVL2-1B-DA-Medical) **← Recommended**
- `vllm`: vLLM server with vision model (requires GPU server)

**OCR Providers:**
- `none`: Disabled
- `tesseract`: Tesseract OCR (requires pytesseract + system Tesseract)

## 🔧 System Dependencies

Depending on your provider choices, you may need:

**For Tesseract OCR:**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# macOS
brew install tesseract

# Windows
# Download installer from GitHub
```

**For Audio Processing:**
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from ffmpeg.org
```

**For GPU Support:**
- NVIDIA CUDA drivers
- Docker with GPU support (nvidia-docker)

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check with version info |
| `/api/chat` | POST | Chat with RAG context and safety checks |
| `/api/rag/ingest` | POST | Add documents to RAG store |
| `/api/stt` | POST | Speech-to-text transcription |
| `/api/tts` | POST | Text-to-speech synthesis |
| `/api/vision` | POST | Image OCR and question answering |

See API documentation at `/docs` when running locally.

## 🛡️ Safety Features

### Red-Flag Detection
Automatically detects emergency symptoms:
- Chest pain, shortness of breath
- Severe bleeding, loss of consciousness
- Stroke symptoms, seizures
- Suicidal thoughts, overdose
- Severe allergic reactions

### Response Format
All responses include:
- Main message
- Safety disclaimer
- Emergency notice (if red flags detected)
- Citations from RAG (if available)

## 📊 Error Handling

The application includes comprehensive error handling:

- **Custom Exceptions**: Typed exceptions for different error scenarios
- **Retry Logic**: Exponential backoff for external API calls
- **Validation**: Input validation with detailed error messages
- **Logging**: Structured logging with multiple levels
- **Graceful Degradation**: Fallback to simpler providers when advanced ones fail

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

## 📈 Monitoring & Logging

**Log Files** (when `ENABLE_FILE_LOGGING=true`):
- `logs/mediscope.log`: All application logs
- `logs/errors.log`: Error-level logs only

**Log Rotation**: Automatic rotation at 10MB, keeps 5 backups

**Health Monitoring**: Use `/api/health` endpoint

## 🚢 Production Deployment

**See [PRODUCTION.md](PRODUCTION.md) for detailed checklist.**

Key production recommendations:
1. Set `ENVIRONMENT=production`
2. Use `LOG_LEVEL=WARNING` or `ERROR`
3. Disable `DEMO_MODE`
4. Configure proper CORS origins
5. Use reverse proxy (Nginx) for HTTPS
6. Implement rate limiting
7. Set up monitoring and alerts
8. Use Gunicorn with multiple workers
9. Regular backups of RAG store

## 🔐 Security Considerations

- Never commit `.env` file
- Use environment variables for secrets
- Implement authentication/authorization for production
- Validate all user inputs
- Use HTTPS in production
- Implement rate limiting
- Regular security audits
- Keep dependencies updated

## 📦 Optional: vLLM Setup

To use local LLM with vLLM:

1. Uncomment `vllm` service in `docker-compose.yml`
2. Configure in `.env`:
   ```bash
   LLM_PROVIDER=vllm
   VLLM_URL=http://vllm:8000
   ```
3. Ensure GPU passthrough in Docker Desktop
4. Start services: `docker-compose up --build`

**Example vLLM command:**
```bash
vllm serve "OpenGVLab/Mini-InternVL2-1B-DA-Medical" \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype half \
  --max-model-len 2048
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Ensure all tests pass
5. Submit pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: This README and [PRODUCTION.md](PRODUCTION.md)
- **Logs**: Check `logs/` directory for errors

## 🔄 Recent Updates

### Version 0.1.0 (Production-Ready)
- ✅ Comprehensive error handling across all services
- ✅ Retry logic with exponential backoff
- ✅ Enhanced logging with rotation
- ✅ Input validation for all endpoints
- ✅ Custom exception hierarchy
- ✅ Health checks for dependencies
- ✅ Production deployment guide
- ✅ Improved configuration validation
- ✅ Better frontend error handling
- ✅ Docker health checks

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [vLLM Documentation](https://docs.vllm.ai/)
- [Transformers Documentation](https://huggingface.co/docs/transformers/)

---

**Remember**: This is an educational tool. Always seek professional medical advice for health concerns.

## 🏠 Local AI with LM Studio (Recommended Setup)

Run medical AI models **completely offline** on your own computer!

### Why LM Studio?

✅ **100% Private** - No data leaves your computer  
✅ **No API Costs** - Free to use, no subscriptions  
✅ **Offline Capable** - Works without internet (after model download)  
✅ **Medical Specialized** - Use qwen3-medical-gguf for accurate medical responses  
✅ **Easy Setup** - User-friendly interface, no command line needed  

### Quick LM Studio Setup

```bash
# 1. Download LM Studio
Visit: https://lmstudio.ai/

# 2. Install and open LM Studio

# 3. Search and download model:
towardsinnovationlab/qwen3-medical-gguf (Q4_K_M recommended - 3.5GB)

# 4. Load model and start server (Port: 1234)

# 5. Configure MediScope in .env:
LLM_PROVIDER=lmstudio
LLM_MODEL=towardsinnovationlab/qwen3-medical-gguf
LMSTUDIO_URL=http://localhost:1234

VISION_PROVIDER=internvl  # For medical image analysis
OCR_PROVIDER=tesseract    # For text extraction

# 6. Install ML dependencies:
cd backend
pip install -r requirements-ml.txt

# 7. Run MediScope:
run.bat
```

**📖 Detailed Guide:**
- English: [LMSTUDIO_SETUP.md](LMSTUDIO_SETUP.md)


### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8GB | 16GB |
| Storage | 10GB | 20GB |
| CPU | Modern multi-core | i5/Ryzen 5 or better |
| GPU | Not required | Recommended for vision |

### Model Options

| Model Size | RAM Needed | Speed | Quality | Use Case |
|-----------|------------|-------|---------|----------|
| Q3_K_M (2.5GB) | 6GB | Fast | Good | Testing, low-end PCs |
| Q4_K_M (3.5GB) | 8GB | Medium | Better | **Recommended** |
| Q5_K_M (4.5GB) | 10GB | Slower | Best | High accuracy needs |

