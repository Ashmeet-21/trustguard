# TrustGuard — Project Context

Read this first. It is the single source of truth for project state, so new sessions don't need to re-explore the codebase.
**Keep it updated** when something meaningful changes (new feature, status change, decision made).

## What it is
Multi-modal identity verification platform (portfolio project by Ashmeet Singh, GitHub: Ashmeet-21/trustguard, public, branch `master`).
4 detection agents → session orchestrator → weighted risk engine → PASS / REVIEW / FAIL, with quality gates and audit trail.

## About the user (how to work with them)
- Knows **basic Python only**, no ML background. Explain in plain English, keep code simple and interview-explainable.
- No over-engineering, no complex DI/patterns. Small, surgical changes.
- Project is for **job interviews / portfolio**: never overclaim accuracy (see "Honest gaps").
- Decided 2026-10-08: **keep the Python + Next.js stack** (ML libs are Python-only); walk the user through code as we touch it.

## Commands (Windows, run from project root)
```
venv\Scripts\python -m pytest tests/ -q        # 92 tests, ~30-50s (deepfake test loads ViT model)
venv\Scripts\python -m backend.main             # backend on :8000, docs at /docs
cd frontend && npm run dev                      # frontend on :3000 (proxies /api → :8000)
cd frontend && npm run build                    # verify frontend builds
docker-compose up --build                       # both services
```
- Python 3.11.8, venv at `venv/`. Quote paths (folder is under OneDrive with spaces possible).
- Tests set `TESTING=true` → rate limiting disabled. Test DB = `./test_trustguard.db`.

## Backend layout (`backend/`)
- `main.py` — creates singletons: HFGateway, DeepfakeDetector, LivenessDetector, VoiceDetector, BehaviorAnalyzer, RiskEngine, SessionOrchestrator, AuditReporter; registers 11 routers.
- `core/`
  - `deepfake_detector.py` — model `dima806/deepfake_vs_real_image_detection` (ViT). Two modes: `api` (HF_TOKEN set → HF Inference API) or `local` (torch). Attrs are private: `_mode`, `_device`, `_model`. Methods: `predict_image`, `predict_video` (frame sampling + majority vote), `batch_predict`.
  - `liveness_detector.py` — 6 OpenCV/MediaPipe checks (face mesh, LBP texture, FFT frequency, YCrCb color, Canny edges, Laplacian sharpness) → weighted score. `is_live = score >= 0.7`. Risk: ≥0.7 LOW, ≥0.5 MEDIUM, ≥0.3 HIGH, else CRITICAL.
  - `voice_detector.py` — HF API (`MattyB95/AST-ASVspoof2019-Synthetic-Voice-Detection`) primary; scipy spectral fallback (flatness, zero-crossing, energy variation).
  - `behavior_analyzer.py` — rule-based: typing speed/rhythm, mouse speed/straightness. Human if score ≥ 0.6.
  - `risk_engine.py` — weights image 0.30, video(=liveness) 0.25, voice 0.25, behavior 0.20; renormalized over available signals. Agent "FLAGGED" if score < 60. FAIL: score<40 or any CRITICAL or 2+ flagged. REVIEW: score<70 or 1 flagged. else PASS.
  - `session_orchestrator.py` — in-memory sessions with expiry: `create_session`, `run_session(session_id, image_path, audio_path, behavior_data)`, `get_session_state`.
  - `quality_gates.py` — replay (SHA256 hash seen in another session), min 2 signals, signal agreement (flags if risk-level gap ≥ 2 — **README wrongly says 3+**).
  - `audit_reporter.py` — JSON reports in `backend/audit_reports/` + DB AuditLog.
  - `hf_gateway.py` — HF InferenceClient wrapper with retries.
- `api/` — `routes_*.py` (deepfake, liveness, voice, behavior, session, audit, kyc, auth, user, analytics, general) + `schemas.py` (Pydantic v2; password rules enforced in schema validator → 422). `routes_auth.py:38` has a leftover duplicate password check (dead code, returns 400).
- `database/` — SQLAlchemy + SQLite. Models: User, VerificationLog, AuditLog.
- `utils/` — `config.py` (all env vars), `file_handling.py`, `rate_limiter.py` (slowapi), `logging.py` (loguru).

## Auth rules
- JWT required: `/user/*`, `/audit/*`, `/analytics/*`. Optional on `/session/*` (links to user). Others public.
- Password: 12+ chars, upper, lower, digit, special.
- Tests use the `auth_headers` fixture in `tests/conftest.py`.

## Frontend (`frontend/`, Next.js 16.1.6, React 19, Tailwind v4, TypeScript)
- Pages: `/` landing, `/login`, `/verify` (5-step wizard, auth), `/dashboard` (analytics, auth).
- Components: CameraCapture, AudioRecorder, BehavioralTracker, TrustScoreGauge, AgentStatusCard, StepWizard, Navbar.
- `lib/api.ts` typed client, `lib/AuthContext.tsx` auth state. API base via `NEXT_PUBLIC_API_URL` / next.config rewrites.
- Dark theme, gradient #00d4ff → #7b2ff7. Next 16 gotcha: `useRef<T>(undefined)` needs an initial value.

## Deploy / CI
- Backend: `render.yaml` (Docker, `requirements-prod.txt` = no torch → needs HF_TOKEN). Has `CORS_ORIGINS="*"` — should be locked to frontend URL.
- Frontend: `netlify.toml` (base `frontend`, @netlify/plugin-nextjs).
- **No live demo URL yet** (GitHub "website" field empty). Unknown if Render/Netlify are actually running.
- CI: `.github/workflows/ci.yml` — fixed 2026-10-08 to trigger on `master` (was `main`, so it had never run). Not yet confirmed green on GitHub.

## Known gotchas
- bcrypt must be pinned `4.1.3` (5.x breaks passlib).
- Pydantic v2: `model_config = ConfigDict(from_attributes=True)`.
- Windows: SQLite test DB removal can fail → `engine.dispose()` first.
- mediapipe 0.10.9 pulls opencv-contrib — don't add opencv separately in prod reqs.

## Honest gaps (say this in interviews, don't hide it)
- No real-world accuracy benchmark yet. "99%+" is the **model author's** claim, not ours.
- Liveness/voice/behavior thresholds are hand-tuned; liveness tested on 1 image (`datasets/test_images/test_face.jpg`).
- False positive / negative rates unknown.

## Polish plan (started 2026-10-08)
1. [x] Fix stale tests (11 failing → 92 passing) + CI branch fix — **uncommitted, not pushed yet**
2. [ ] Benchmark script (`benchmarks/`) on a labeled dataset the model was NOT trained on (dima806 likely trained on a Kaggle deepfake set — avoid it to prevent leakage). Report accuracy / FPR / FNR, tune thresholds.
3. [ ] Live demo (Render + Netlify), add URL to README + GitHub website field, add repo topics.
4. [ ] README rewrite: demo link + GIF at top, results table, "Limitations & next steps", fix 3+ vs 2 gate wording, drop "99%" as own claim.
5. [ ] Cleanups: CORS lock, remove dead password check in routes_auth, root `test_setup.py`.
6. [ ] Walk user through backend file by file (risk_engine → quality_gates → behavior → orchestrator → detectors).
