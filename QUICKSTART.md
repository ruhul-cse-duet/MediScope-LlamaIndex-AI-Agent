# Quick Start Guide - MediScope AI Agent

## 🚀 5-Minute Setup

### Step 1: Setup (One Time Only)

**Option B: Manual Setup**
```bash
# 1. Navigate to project
cd "E:\Data Science\ML_and_DL_project\NLP Project\MediScope LlamaIndex AI Agent"

# 2. Create virtual environment
cd backend
python -m venv .venv

# 3. Activate virtual environment
.venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file
cd ..
copy .env.example .env

# 6. Create directories
mkdir data
mkdir logs
```

### Step 2: Configure

Edit `.env` file (optional, works with defaults):
```
ENVIRONMENT=local
LLM_PROVIDER=none      # Use 'openai' if you have API key
OPENAI_API_KEY=        # Add your key if using OpenAI
```

### Step 3: Run

**Option A: Use Script (Easiest)**
```bash
# Just double-click run.bat
# or run from terminal:
run.bat
```

**Option B: Manual**
```bash
# Must be in backend directory!
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Step 4: Access

Open browser to: **http://localhost:8000**

---

## ⚠️ Common First-Time Issues

### Issue 1: "Module not found" error

**Fix:** You're in the wrong directory!
```bash
# WRONG - Running from project root
E:\...\MediScope LlamaIndex AI Agent> uvicorn app.main:app

# CORRECT - Running from backend directory
E:\...\MediScope LlamaIndex AI Agent\backend> uvicorn app.main:app
```

### Issue 2: "uvicorn not found"

**Fix:** Virtual environment not activated
```bash
cd backend
.venv\Scripts\activate
# You should see (.venv) in your prompt
```

### Issue 3: "Permission denied"

**Fix:** Run as administrator or create directories manually
```bash
mkdir data
mkdir logs
```

### Issue 4: Configuration errors

**Fix:** Make sure .env file exists
```bash
# Check if .env exists
dir .env

# If not, create it
copy .env.example .env
```

---

## 📝 Correct Command Sequence

```bash
# 1. Start from project root
cd "E:\Data Science\ML_and_DL_project\NLP Project\MediScope LlamaIndex AI Agent"

# 2. Go to backend directory
cd backend

# 3. Activate virtual environment
.venv\Scripts\activate

# 4. Run server (from backend directory!)
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## ✅ Success Indicators

When everything is working, you'll see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started reloader process [xxxx]
INFO:     Started server process [xxxx]
INFO:     Waiting for application startup.
2024-02-07 | INFO | __main__ | Starting MediScope v0.1.0
2024-02-07 | INFO | __main__ | Environment: local
2024-02-07 | INFO | __main__ | LLM Provider: none
2024-02-07 | INFO | __main__ | Application startup complete
INFO:     Application startup complete.
```

Then open browser to http://localhost:8000 and you should see the interface!

---

## 🎯 What to Do After Starting

1. **Test Health Check**
   - Go to: http://localhost:8000/api/health
   - Should show: `{"status": "ok", ...}`

2. **Try the Interface**
   - Go to: http://localhost:8000
   - Type a message in the chat
   - Click "Send to Agent"

3. **Check Logs**
   - Application logs: `logs/mediscope.log`
   - Error logs: `logs/errors.log`

---

## 🔧 Quick Commands Reference

```bash

# Run server
run.bat

# Or manually:
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Stop server
CTRL+C

# Check configuration
cd backend
python -c "from app.core.config import settings; print(settings.dict())"

# Run tests
cd backend
pytest tests/ -v
```

---

## 📚 Need More Help?

- **Errors?** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Setup details?** See [README.md](README.md)
- **Production?** See [PRODUCTION.md](PRODUCTION.md)
- **Changes?** See [CHANGELOG.md](CHANGELOG.md)

---

## 🎓 Next Steps After Setup

### Enable ML Features (Optional)

1. Install ML dependencies:
   ```bash
   cd backend
   pip install -r requirements-ml.txt
   ```

2. Update `.env`:
   ```
   # For better LLM responses
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your-key-here
   
   # For voice features
   STT_PROVIDER=faster_whisper
   TTS_PROVIDER=gtts
   
   # For image analysis
   OCR_PROVIDER=tesseract
   VISION_PROVIDER=internvl
   
   # For better RAG
   RAG_PROVIDER=llamaindex
   ```

3. Install system dependencies:
   - Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
   - FFmpeg: https://ffmpeg.org/download.html

### Add Medical Documents

```bash
# Place documents in data/documents/
mkdir data\documents
# Copy .txt, .pdf, .docx files here

# Or use the API:
# POST to /api/rag/ingest with document text
```

---

## 💡 Pro Tips

1. **Use the scripts** - `setup.bat` and `run.bat` handle everything
2. **Always from backend** - Run uvicorn from backend directory
3. **Check logs first** - Most issues are logged in `logs/`
4. **Start simple** - Use defaults first, then add features
5. **Read errors carefully** - They usually tell you exactly what's wrong

---

## 🚨 Emergency Reset

If everything is broken:

```bash
# 1. Stop server (CTRL+C)

# 2. Delete virtual environment
cd backend
rmdir /s /q .venv

# 3. Run setup again
cd ..
setup.bat

# 4. Edit .env if needed

# 5. Run server
run.bat
```

---

## ✨ You're Ready!

Once you see "Application startup complete", you're all set!

Open http://localhost:8000 and start using MediScope! 🎉
