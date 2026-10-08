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
venv\Scripts\python -m pytest tests/ -q        # 105 tests, ~35s (deepfake test loads ViT model)
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
  - `deepfake_detector.py` — model **`buildborderless/CommunityForensics-DeepfakeDet-ViT`** (switched 2026-10-08 from dima806 after benchmark; single output = logit → sigmoid = p(fake)). Three backends via `config.DEEPFAKE_BACKEND` / `backend=` arg:
    - `onnx` (**default, production**): `backend/models/deepfake_vit_int8.onnx` (24 MB, per-channel int8 MatMul/Gemm only — Conv quantization breaks ORT CPU) run with onnxruntime; `preprocess()` reproduces the CLIPImageProcessor (shortest edge 440 bicubic, crop 384, CLIP mean/std) — matches PyTorch within 0.0055. Regenerate with `python -m scripts.export_deepfake_onnx`. Server peak RSS ~260 MB, ~80 ms/image, no torch import.
    - `api`: HF Inference API — account is out of free credits (402), so not usable without paying.
    - `local`: transformers pipeline (dev; `model_name=` always uses this so the benchmark can compare models).
    All feed `_fake_probability()`. Fake if p(fake) > `DEEPFAKE_THRESHOLD`. Probabilities rounded to 6 dp. **Fails closed**: API error → `DetectorUnavailable` (→ HTTP 503).
  - `liveness_detector.py` — 6 OpenCV/MediaPipe checks (face mesh, LBP texture, FFT frequency, YCrCb color, Canny edges, Laplacian sharpness) → weighted score. `is_live = score >= 0.7`. Risk: ≥0.7 LOW, ≥0.5 MEDIUM, ≥0.3 HIGH, else CRITICAL.
  - `voice_detector.py` — HF API (`MattyB95/AST-ASVspoof2019-Synthetic-Voice-Detection`) primary; scipy spectral fallback (flatness, zero-crossing, energy variation).
  - `behavior_analyzer.py` — rule-based: typing speed/rhythm, mouse speed/straightness. Human if score ≥ 0.6.
  - `risk_engine.py` — weights image 0.30, video(=liveness) 0.25, voice 0.25, behavior 0.20; renormalized over available signals. Agent "FLAGGED" if score < 60. FAIL: score<40 or any CRITICAL or 2+ flagged. REVIEW: score<70 or 1 flagged. else PASS.
  - `session_orchestrator.py` — in-memory sessions with expiry: `create_session(user_id)`, `run_session(...)`, `get_session_state`. Sessions have an owner (`user_id`, None = anonymous) and run **once** (status must be "created"). Any crashed agent → PASS downgraded to REVIEW (fail closed).
  - `quality_gates.py` — replay (SHA256 seen in another session), min 2 signals, signal agreement (risk gap ≥ 2). `apply_gates()` enforces them: replay → FAIL, other failures → PASS becomes REVIEW.
  - `audit_reporter.py` — JSON reports in `backend/audit_reports/` + DB AuditLog. Reports store `user_id`; only the owner can read them. `get_report` only accepts UUIDs (path traversal guard).
  - `hf_gateway.py` — HF InferenceClient wrapper; one `_call_with_retries` used by image + audio. Defines `DetectorUnavailable`.
- `api/` — `routes_*.py` (deepfake, liveness, voice, behavior, session, audit, kyc, auth, user, analytics, general) + `schemas.py` (only request models + auth/history responses; password rules enforced in schema → 422; behavior lists capped 2000/5000).
- `utils/file_handling.py` — `save_temp_file(file, kind)` is the ONLY way to save uploads: UUID name, size limit, magic-byte content check (`kind` = image/video/audio). Use it for every new upload endpoint.
- `database/` — SQLAlchemy + SQLite. Models: User, VerificationLog, AuditLog.
- `utils/` — `config.py` (all env vars), `file_handling.py`, `rate_limiter.py` (slowapi), `logging.py` (loguru).

## Auth rules
- JWT required: `/user/*`, `/audit/*`, `/analytics/*`. Optional on `/session/*` (links to user; a user's session is private to them). Others public.
- Shared decoder `_user_from_token` in routes_user.py: verifies signature, expiry, `iss="trustguard"`, user exists + is_active.
- Password: 12-72 chars, upper, lower, digit, special. Login lowercases email (registration does too).
- No roles: any registered user sees platform-wide `/analytics` (incl. other uploads' filenames) — known gap, needs an admin role.
- Tests use the `auth_headers` fixture in `tests/conftest.py`.

## Frontend (`frontend/`, Next.js 16.1.6, React 19, Tailwind v4, TypeScript)
- Pages: `/` landing, `/login`, `/verify` (photo → voice → typing → result, auth), `/dashboard` (analytics, auth).
- Components: CameraCapture, AudioRecorder, BehavioralTracker, StepWizard (vertical), Navbar, **VerificationDocument** (result rendered as an ID-document data page with photo, ink-stamp decision, per-check readings and a 2×44-char MRZ that encodes the result; also used as the landing-page specimen).
- `lib/api.ts` typed client, `lib/AuthContext.tsx` auth state. API base via `NEXT_PUBLIC_API_URL` / next.config rewrites.
- **Design system (redesigned 2026-10-08, "identity document" direction)** — tokens in `globals.css` `@theme`: paper #eef1ef, sheet #f9faf8, ink #16233a, one action colour seal #23408e, pass/review/fail ink colours. Fonts: Schibsted Grotesk (everything) + IBM Plex Mono (MRZ + session IDs only). Utility classes: `.btn`, `.btn-quiet`, `.link`, `.field`, `.sheet`, `.note note-pass|review|fail`, `.mrz`, `.figures` (tabular nums). Rules: light theme only, no gradients/glass/glow, no all-caps labels, left-aligned, only motion = MRZ print-in on result (respects reduced motion). Landing checks table lists what each check *doesn't* catch — keep that honesty.
- Dashboard no longer shows filenames (privacy). Next 16 gotcha: `useRef<T>(undefined)` needs an initial value.

## Deploy / CI
- **LIVE** (verified 2026-10-08): frontend https://steady-semolina-01c7cf.netlify.app (Netlify site id c8bed503-…), backend https://trustguard-bgba.onrender.com (Render free tier, auto-deploys `master`, sleeps when idle ~1 min cold start).
  - Browser calls same-origin `/api/*` → Next.js rewrite on Netlify proxies to backend (`NEXT_PUBLIC_API_URL`).
  - `trustguard-backend.onrender.com` is a DIFFERENT, suspended service — not ours to use; render.yaml `name:` doesn't match the live one, so env vars are really managed in the Render dashboard.
  - `render.yaml` CORS now = Netlify URL (also set it in the Render dashboard).
- **2026-10-08 fix: production now uses the bundled ONNX model (no HF needed).** HF_TOKEN should be REMOVED from Render (otherwise voice audio is first sent to HF, which fails anyway). Dockerfile no longer copies `.env.example` into the image (it carried a public JWT secret fallback).
- (History) **Prod deepfake check was broken:** HF API returns 401 Invalid username or password (confirmed in Render logs 2026-10-08) → `/detect/deepfake/image` returns 503, sessions run without image_agent. Model `dima806/...` IS live on hf-inference, so cause = HF_TOKEN in Render (invalid/expired/missing "Inference Providers" permission/out of free credits). User must fix in Render dashboard; check Render logs for "HF image_classification failed".
  - Before the fail-closed fix this was hidden (every image was silently called REAL).
- Voice model `MattyB95/AST-ASVspoof2019...` is NOT served by any HF inference provider → prod voice always uses local spectral fallback.
- `datasets/test_images/test_face.jpg` scores liveness 0.148 (SPOOF) locally and in prod → liveness thresholds need calibration (benchmark step).
- GitHub repo homepage + topics set; README has live links + real CI badge.
- CI: `.github/workflows/ci.yml` — fixed 2026-10-08 to trigger on `master` (was `main`, so it had never run). Not yet confirmed green on GitHub.

## Known gotchas
- bcrypt must be pinned `4.1.3` (5.x breaks passlib).
- Pydantic v2: `model_config = ConfigDict(from_attributes=True)`.
- Windows: SQLite test DB removal can fail → `engine.dispose()` first.
- mediapipe 0.10.9 pulls opencv-contrib — don't add opencv separately in prod reqs.

## Honest gaps (say this in interviews, don't hide it)
- **Benchmark done 2026-10-08** (`benchmarks/run_benchmark.py`, results in `benchmarks/RESULTS.md`): on DeepFakeFace (unseen generators) the deepfake model catches 1/99 fakes, AUC 0.405 (worse than guessing). Sanity check on its training-style data (Hemg/deepfake-and-real-images): 100/100 → our pipeline is correct, the model doesn't generalize. All "99%" claims removed from README + landing page.
  - Script reads remote zips via `HfFileSystem` (downloads only sampled images to gitignored `datasets/deepfakeface/`). pyarrow installed in venv only for the one-off sanity check (not in requirements).
- Liveness/voice/behavior thresholds are hand-tuned; liveness tested on 1 image (`datasets/test_images/test_face.jpg`).
- False positive / negative rates unknown.

## Known limitations (not fixed yet)
- Routes are `async def` but call blocking ML inference → one slow request blocks the server. Fix = sync `def` routes, BUT mediapipe FaceMesh isn't thread-safe, so needs a lock first.
- Rate limiter + sessions + replay hashes are in-memory → reset on restart, don't work across multiple workers (would need Redis).
- `render.yaml` has `CORS_ORIGINS="*"` → set to the real Netlify URL once deployed.
- KYC endpoint has its own verdict rules separate from the risk engine (can disagree with trust_score).

## Polish plan (started 2026-10-08)
1. [x] Fix stale tests + CI branch fix (commit 42f2383). CI then caught missing `scipy` in requirements.txt.
1b. [x] Security review & cleanup (2026-10-08): 9 vulns/bugs fixed, redundant code removed, 105 tests.
2. [x] Benchmark (2026-10-08) — dima806 failed on unseen fakes (AUC 0.41).
2b. [x] Compared 8 hosted models (`benchmarks/MODEL_COMPARISON.md`, `--compare`), switched to CommunityForensics: AUC 0.88, acc 80%, 0% false positives; catches 100% text2img / 76% inpainting / 3% face-swap. Threshold left at 0.5 on purpose (tuning on the test set = overfitting; would need a separate validation set).
   - Live API output for this model NOT verified yet (needs working HF_TOKEN). Unit test assumes hosted API returns `[{"label": "LABEL_0", "score": p_fake}]` like the local pipeline.
3. [ ] Live demo (Render + Netlify), add URL to README + GitHub website field, add repo topics.
4. [ ] README rewrite: demo link + GIF at top, results table, "Limitations & next steps", drop "99%" as own claim.
5. [ ] Cleanups: CORS lock, root `test_setup.py`.
6. [ ] Walk user through backend file by file (risk_engine → quality_gates → behavior → orchestrator → detectors).
