# TrustGuard — Multi-Modal Identity Verification Platform

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.128-green)
![Next.js 16](https://img.shields.io/badge/Next.js-16-black)
[![CI](https://github.com/Ashmeet-21/trustguard/actions/workflows/ci.yml/badge.svg)](https://github.com/Ashmeet-21/trustguard/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/License-MIT-yellow)

**🔗 Live demo: [steady-semolina-01c7cf.netlify.app](https://steady-semolina-01c7cf.netlify.app/)** · **API docs: [trustguard-bgba.onrender.com/docs](https://trustguard-bgba.onrender.com/docs)**

> Hosted on free tiers — the backend sleeps when idle, so the first request can take ~1 minute to wake it up.

A full-stack identity verification platform that combines **4 AI detection agents** — deepfake detection, liveness checking, voice analysis, and behavioral biometrics — into a single trust score through an orchestrated pipeline with quality gates and audit trails.

Built with FastAPI, Next.js, OpenCV, MediaPipe, HuggingFace Transformers, and a Vision Transformer model.

---

## Benchmark — does the deepfake model work on fakes it has never seen?

The original model (`dima806/deepfake_vs_real_image_detection`) reported **99.27%** accuracy — on its own
training data. I tested it on [DeepFakeFace](https://huggingface.co/datasets/OpenRL/DeepFakeFace), a dataset
it was **not** trained on (100 real photos + 99 fakes from Stable Diffusion text-to-image, inpainting and
InsightFace face swap). It caught **1 of 99** fakes (AUC 0.41 — worse than guessing), even though a sanity
check on images like its training data scored 100/100. The pipeline was fine; the model didn't generalize.

So I benchmarked **8 pretrained models** on the same images and switched to the best one:

| | Original model | **Current model** (CommunityForensics ViT) |
|---|---|---|
| AUC (0.5 = guessing, 1.0 = perfect) | 0.41 | **0.88** |
| Accuracy | 50% | **80%** |
| Fakes caught | 1% | **60%** |
| Real people wrongly flagged | 1% | **0%** |
| Caught by generator: text-to-image / inpainting / face swap | 3% / 0% / 0% | **100% / 76% / 3%** |

**Remaining weakness:** face swaps are almost never caught — most of the pixels are a genuine photo.
That's why TrustGuard doesn't rely on one check: liveness, voice, behavior and the quality gates still apply,
and a crashed or unavailable detector can never produce an automatic PASS.

Details: [benchmarks/RESULTS.md](benchmarks/RESULTS.md) · all 8 models: [benchmarks/MODEL_COMPARISON.md](benchmarks/MODEL_COMPARISON.md) ·
reproduce with `python -m benchmarks.run_benchmark` (`--compare` for the model comparison).

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│  Next.js Frontend (React 19 + TypeScript + Tailwind)              │
│  ├── Landing Page         (feature overview, how-it-works)        │
│  ├── Verify Wizard        (selfie → voice → behavior → result)   │
│  └── Dashboard            (analytics, risk distribution, history) │
└────────────────────────────┬──────────────────────────────────────┘
                             │ API Proxy (/api → :8000)
┌────────────────────────────▼──────────────────────────────────────┐
│  FastAPI Backend                                                   │
│  ├── JWT Authentication    (register/login, token-protected)       │
│  ├── Rate Limiting         (slowapi, per-IP throttling)            │
│  └── CORS Middleware                                               │
├────────────────────────────────────────────────────────────────────┤
│  Session Orchestrator                                              │
│  │   Creates session → routes data to agents → collects results   │
│  │                                                                 │
│  ├── Agent 1: Deepfake Detector    (ViT, picked by benchmark)     │
│  ├── Agent 2: Liveness Detector    (6 OpenCV/MediaPipe checks)    │
│  ├── Agent 3: Voice Detector       (HF API + spectral fallback)   │
│  └── Agent 4: Behavior Analyzer    (keystroke + mouse patterns)   │
│                                                                    │
│  Risk Engine ──► Weighted scoring → PASS / REVIEW / FAIL          │
│  Quality Gates ──► Replay protection, signal agreement, minimums  │
│  Audit Reporter ──► JSON reports + database logging               │
├────────────────────────────────────────────────────────────────────┤
│  Database (SQLAlchemy + SQLite)                                    │
│  ├── Users                 (accounts, hashed passwords)            │
│  ├── VerificationLogs      (scan results, risk levels)             │
│  └── AuditLogs             (compliance trail)                      │
└────────────────────────────────────────────────────────────────────┘
```

---

## Detection Agents

### 1. Deepfake Detection
- Pretrained **Vision Transformer (ViT)** from HuggingFace
- Single image, video (frame sampling + majority vote), and batch modes
- Returns confidence score + risk level (LOW/MEDIUM/HIGH/CRITICAL)

### 2. Liveness Detection
Six independent checks on every image:

| Check | Technique | What It Catches |
|-------|-----------|-----------------|
| Face Detection | MediaPipe Face Mesh | No face = spoof |
| Texture Analysis | Local Binary Patterns | Flat printed photos |
| Frequency Analysis | FFT | Screen moire patterns |
| Color Distribution | YCrCb Entropy | Washed-out prints |
| Edge Density | Canny Edge Detection | Unnatural sharpness |
| Sharpness | Laplacian Variance | Photo-of-photo blur |

Weighted scoring → single liveness score with LIVE/SPOOF classification.

### 3. Voice Analysis
- **Primary**: HuggingFace Inference API (`AST-ASVspoof2019` model)
- **Fallback**: Local spectral analysis (3 checks: spectral flatness, zero-crossing rate, energy variation)
- Detects AI-generated and cloned voices

### 4. Behavioral Biometrics
Rule-based analysis — no ML training required:
- **Typing speed** — bots type < 30ms between keys, humans 50-300ms
- **Typing rhythm** — variance in intervals (bots are robotic)
- **Mouse speed** — bots teleport, humans move smoothly
- **Mouse straightness** — path efficiency ratio

---

## Risk Engine & Decision Pipeline

```
Agent Scores ──► Weighted Average ──► Trust Score (0-100) ──► Decision
                 ├── Deepfake:  30%
                 ├── Liveness:  25%     PASS:   score >= 70, no critical agents
                 ├── Voice:     25%     REVIEW: score 40-69 or 1 high-risk agent
                 └── Behavior:  20%     FAIL:   score < 40 or critical agent
```

**Quality gates** run after the agents and can only make the decision stricter:
- **Replay protection** — SHA256 hash check; an image already used in another session → **FAIL**
- **Minimum signals** — at least 2 agents must complete, otherwise PASS → **REVIEW**
- **Signal agreement** — agents 2+ risk levels apart (e.g. LOW vs HIGH) → PASS becomes **REVIEW**

**Fail closed** — if a detector crashes or its API is down, the session can never auto-PASS (→ REVIEW), and standalone endpoints return 503 instead of guessing.

---

## API Endpoints

| Method | Endpoint | Description | Auth | Rate Limit |
|--------|----------|-------------|------|------------|
| `POST` | `/api/v1/auth/register` | Create account | — | 5/min |
| `POST` | `/api/v1/auth/login` | Get JWT token | — | 5/min |
| `GET` | `/api/v1/user/me` | User profile | JWT | — |
| `GET` | `/api/v1/user/me/history` | Verification history | JWT | — |
| `POST` | `/api/v1/session/create` | Create verification session | Optional | 10/min |
| `POST` | `/api/v1/session/{id}/verify` | Run multi-agent verification | Optional | 5/min |
| `GET` | `/api/v1/session/{id}` | Get session state | — | — |
| `POST` | `/api/v1/detect/deepfake/image` | Deepfake check (image) | — | 10/min |
| `POST` | `/api/v1/detect/deepfake/video` | Deepfake check (video) | — | 5/min |
| `POST` | `/api/v1/detect/batch` | Batch deepfake (up to 10) | — | 3/min |
| `POST` | `/api/v1/detect/liveness` | Liveness check (image) | — | 10/min |
| `POST` | `/api/v1/detect/liveness/video` | Liveness check (video) | — | 5/min |
| `POST` | `/api/v1/detect/voice` | Voice analysis | — | 10/min |
| `POST` | `/api/v1/detect/voice/batch` | Batch voice analysis | — | 3/min |
| `POST` | `/api/v1/detect/behavior` | Behavioral biometrics | — | 10/min |
| `POST` | `/api/v1/verify/kyc` | Full KYC pipeline | — | 5/min |
| `GET` | `/api/v1/audit/{session_id}` | Get audit report | JWT | — |
| `GET` | `/api/v1/audit/` | Recent audit reports | JWT | — |
| `GET` | `/api/v1/analytics/summary` | Platform statistics | JWT | — |
| `GET` | `/api/v1/analytics/recent` | Recent verifications | JWT | — |
| `GET` | `/health` | Health check + model status | — | — |

> **Auth levels**: **JWT** = requires `Authorization: Bearer <token>` header. **Optional** = works without auth, but links results to user account when authenticated. **—** = public, no auth needed.

Interactive docs at **http://localhost:8000/docs** when the server is running.

---

## Quick Start

### Option 1: Local Setup

```bash
# Clone and enter project
git clone https://github.com/Ashmeet-21/trustguard.git
cd trustguard

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set up config
copy .env.example .env       # Windows
# cp .env.example .env       # Mac/Linux

# Start the backend (port 8000)
python -m backend.main
```

```bash
# In a second terminal — start the frontend (port 3000)
cd frontend
npm install
npm run dev
```

- Backend API: **http://localhost:8000/docs**
- Frontend: **http://localhost:3000**

### Option 2: Docker

```bash
docker-compose up --build
```

Runs both backend (port 8000) and frontend (port 3000).

---

## Running Tests

```bash
# All 102 tests
pytest tests/ -v

# By module
pytest tests/test_deepfake_detector.py -v       # Deepfake detector (9 tests)
pytest tests/test_liveness_detector.py -v        # Liveness detector (7 tests)
pytest tests/test_voice_detector.py -v           # Voice detector (6 tests)
pytest tests/test_behavior_analyzer.py -v        # Behavior analyzer (6 tests)
pytest tests/test_risk_engine.py -v              # Risk engine (8 tests)
pytest tests/test_quality_gates.py -v            # Quality gates (8 tests)
pytest tests/test_session_orchestrator.py -v     # Session orchestrator (6 tests)
pytest tests/test_security.py -v                 # Security regressions (9 tests)

# API tests only
pytest tests/test_api_*.py -v                    # All 38 API endpoint tests
```

---

## Example: Full Verification Session

```bash
# 1. Create a session
curl -X POST http://localhost:8000/api/v1/session/create
# → {"session_id": "abc-123", "status": "created"}

# 2. Run verification with image + audio + behavior
curl -X POST http://localhost:8000/api/v1/session/abc-123/verify \
  -F "image=@selfie.jpg" \
  -F "audio=@voice.wav" \
  -F 'behavior_json={"keystrokes":[{"key":"h","timestamp_ms":100}],"mouse_movements":[{"x":10,"y":20,"timestamp_ms":100}]}'
```

Response:
```json
{
  "session_id": "abc-123",
  "trust_score": 82.5,
  "decision": "PASS",
  "overall_risk": "LOW",
  "explanation": [
    "Image appears authentic (confidence: 0.97)",
    "Liveness check passed (score: 0.82)",
    "Voice analysis: human detected",
    "Behavioral patterns consistent with human input"
  ],
  "agents": {
    "image_agent": { "score": 0.97, "risk_level": "LOW" },
    "video_agent": { "score": 0.82, "risk_level": "LOW" },
    "voice_agent": { "score": 0.85, "risk_level": "LOW" },
    "behavior_agent": { "score": 0.78, "risk_level": "LOW" }
  },
  "quality_gates": [
    { "gate": "replay_check", "passed": true },
    { "gate": "minimum_signals", "passed": true },
    { "gate": "signal_agreement", "passed": true }
  ],
  "processing_time_ms": 342.15
}
```

---

## Project Structure

```
trustguard/
├── backend/
│   ├── main.py                       # FastAPI entry point, model initialization
│   ├── api/
│   │   ├── routes_deepfake.py        # Image/video/batch deepfake detection
│   │   ├── routes_liveness.py        # Image/video liveness detection
│   │   ├── routes_voice.py           # Voice analysis endpoints
│   │   ├── routes_behavior.py        # Behavioral biometrics endpoint
│   │   ├── routes_session.py         # Session orchestration endpoints
│   │   ├── routes_audit.py           # Audit report endpoints
│   │   ├── routes_kyc.py             # KYC verification pipeline
│   │   ├── routes_analytics.py       # Platform statistics
│   │   ├── routes_auth.py            # Register/login (JWT)
│   │   ├── routes_user.py            # User profile/history
│   │   ├── routes_general.py         # Health check, root
│   │   └── schemas.py                # Pydantic request/response models
│   ├── core/
│   │   ├── deepfake_detector.py      # ViT-based deepfake detection
│   │   ├── liveness_detector.py      # Multi-signal liveness (6 checks)
│   │   ├── voice_detector.py         # HF API + spectral fallback
│   │   ├── behavior_analyzer.py      # Rule-based keystroke/mouse analysis
│   │   ├── session_orchestrator.py   # Multi-agent session management
│   │   ├── risk_engine.py            # Weighted trust score calculation
│   │   ├── quality_gates.py          # Replay protection, signal validation
│   │   ├── audit_reporter.py         # JSON reports + DB logging
│   │   └── hf_gateway.py            # HuggingFace API wrapper with retries
│   ├── database/
│   │   ├── models.py                 # User, VerificationLog, AuditLog
│   │   └── session.py                # Database connection
│   └── utils/
│       ├── config.py                 # Environment config
│       ├── file_handling.py          # Temp file upload/cleanup
│       ├── rate_limiter.py           # Rate limiting setup
│       └── logging.py                # Loguru structured logging
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx              # Landing page
│   │   │   ├── login/page.tsx        # Login & register page
│   │   │   ├── verify/page.tsx       # 5-step verification wizard (auth required)
│   │   │   └── dashboard/page.tsx    # Analytics dashboard (auth required)
│   │   ├── components/
│   │   │   ├── CameraCapture.tsx     # Webcam + file upload
│   │   │   ├── AudioRecorder.tsx     # Voice recording
│   │   │   ├── BehavioralTracker.tsx # Keystroke/mouse capture
│   │   │   ├── TrustScoreGauge.tsx   # Circular score visualization
│   │   │   ├── AgentStatusCard.tsx   # Per-agent result cards
│   │   │   ├── StepWizard.tsx        # Step progress indicator
│   │   │   └── Navbar.tsx            # Navigation bar (auth-aware)
│   │   └── lib/
│   │       ├── api.ts                # API client (typed, auth headers)
│   │       ├── AuthContext.tsx        # Auth state (login/register/logout)
│   │       └── Providers.tsx          # Client-side provider wrapper
│   ├── next.config.ts                # API proxy rewrites
│   └── package.json
├── tests/                            # 102 tests (17 test files)
├── Dockerfile                        # Backend container
├── docker-compose.yml                # Full-stack orchestration
├── requirements.txt                  # Python dependencies
└── .env.example                      # Configuration template
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend API | FastAPI | Async, auto-generated docs, Pydantic validation |
| Frontend | Next.js 16 + React 19 | App router, TypeScript, server components |
| Styling | Tailwind CSS v4 | Dark theme with cyan→purple gradient accents |
| Deepfake Detection | PyTorch + HuggingFace ViT | Pretrained model — see [benchmark](benchmarks/RESULTS.md) for real-world accuracy |
| Liveness Detection | OpenCV + MediaPipe | Lightweight, no GPU needed, 6 explainable checks |
| Voice Detection | HuggingFace API + scipy | API primary, local spectral fallback |
| Behavioral Analysis | NumPy | Pure rule-based, no training data needed |
| Auth | python-jose + passlib | JWT tokens, bcrypt password hashing |
| Database | SQLAlchemy + SQLite | Zero setup, swappable to PostgreSQL |
| Rate Limiting | slowapi | Per-IP request throttling |
| Testing | pytest | 102 tests covering detectors, API, orchestration, security |
| Logging | Loguru | Structured logging with rotation |

---

## Contact

**Ashmeet Singh**
- GitHub: [github.com/Ashmeet-21](https://github.com/Ashmeet-21)
- LinkedIn: [linkedin.com/in/ashmeet-singh-](https://linkedin.com/in/ashmeet-singh-)
- Email: ashmeetsingh152@gmail.com
