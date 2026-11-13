# TrustGuard — Product plan (written 2026-11-13)

Read with `CLAUDE.md` (code state). This file = what we are building next and why.

## 1. What "real product" means (ASSUMPTION — confirm with Ash)
A portfolio-grade product: works end to end, deployed, **every check measured**, honest copy, and a flow a normal user can finish.
It is NOT a certified KYC / identity product. Out of reach here (non-goals):
- certified attack testing (ISO 30107-3 PAD labs), document/ID check, face-to-ID matching, legal/regulatory sign-off.
- Never claim "bank-grade", "secure", or accuracy we have not measured.

Open product question for Ash: **who is it for?** (a) recruiter/interview demo, (b) a small site that wants a "are you a real person" gate, (c) a real KYC startup. Default = (a)+(b).

## 2. Where we are (measured, 2026-11-13)
| Check | Measured | Weight now |
|---|---|---|
| Face (deepfake) | AUC 0.87, 65% of fakes caught, 0% false positives (199 imgs); face swaps only 6% | 40% |
| Liveness | AUC 0.986 CASIA crops, **0.80 on full photos, 63% of attacks accepted**, 4.9% real rejected | 10% |
| Voice | **not validated** (spectral fallback; HF model not served) | 25% |
| Typing | **not validated** (hand-set rules) | 25% |
| End to end | **never measured** | |

Problem: voice + typing = 50% of the vote and are unmeasured; the only well-measured check is face.

## 3. Success metrics (define before building)
- Per check: real users wrongly rejected % and attacks wrongly accepted % on a labelled set (never tuned on the test set).
- End to end: pass rate over >= 30 real sessions (people with real webcam/mic), and attack acceptance over a scripted attack set.
- Funnel: % of users who finish /verify; % who need a retake.

## 4. Roadmap (ranked, with acceptance criteria)

### R1. Active head-turn challenge (BUILT 2026-11-13, needs real-webcam acceptance tests, see CLAUDE.md)
- Server picks `left` or `right` when the session is created, stores it with a short expiry (e.g. 2 min). The client cannot choose.
- Browser sends a front frame + a turned frame in the same verify call (same session).
- Server computes head yaw from MediaPipe face-mesh landmarks (nose tip vs face edges / ear points). Front frame: yaw near 0. Turned frame: yaw past a threshold in the REQUESTED direction.
- **Mirror gotcha:** check whether `CameraCapture` mirrors the preview. Word the prompt as "turn towards your left shoulder", not screen-left. Test direction on REAL webcam frames (`benchmarks/webcam_test.py` pattern).
- Result feeds the liveness agent (e.g. challenge failed -> liveness agent CRITICAL / session not PASS).
- Acceptance: (a) live user passes >= 9/10 tries; (b) a phone photo tilted on a vertical axis does NOT pass (test with real photo; a flat photo can show apparent yaw, so measure it); (c) replayed static image fails; (d) tests for server-side direction + expiry; (e) copy says plainly: stops static photos/prints, does NOT stop a replayed video.
- Smallest correct change, interview-explainable (plain yaw maths, no new ML model).

### R2. Voice benchmark (next priority after R1)
Same pattern as face/liveness: small public spoof set (e.g. `AnodHuang/ASV_Spoof_2019_LA_SNR_50MB` on HF), train/test split, report AUC + error rates. If voice is near coin-flip, demote its weight and fix the landing copy, like liveness.

### R3. Retake flow
Sessions run once; ~5% of real users are rejected by liveness alone. Needs a clear retry path (new session / retry the failed step) with a limit.

### R4. Consent + data retention
Selfie + voice are biometric data. Need: explicit consent screen before camera/mic, clear statement of what is stored and for how long, delete-my-data option, auto-delete of uploads and audit images. Currently missing.

### R5. Reliability
Async routes block on ML inference (MediaPipe FaceMesh is not thread-safe -> lock first). Render free tier = single worker, ~1 min cold start (notice already added).

### R6. Smaller items
README demo GIF + "Limitations & next steps"; admin role for `/analytics`; phone-width + empty/error states check; remove root `test_setup.py`.

## 5. How to work (agreed with Ash)
- One workstream at a time; one engineer (subagent) per workstream, brief taken from this file. No parallel fan-out; subagents cost tokens (Ash's weekly limit matters most).
- Model: Opus for R1 design/product decisions, Sonnet is enough to build R1; Sonnet for R3-R6.
- Every accuracy claim measured on data we did not tune on. Stay simple and interview-explainable.

## 6. Before any push (ask Ash first)
1. Render dashboard: set `LIVENESS_THRESHOLD=0.12` or delete it (0.7 would reject ~31% of real faces).
2. Branches are stacked (`ui-copy-polish` -> `liveness-benchmark` -> `antispoof-model` -> `liveness-weight-challenge`); merge the newest into master once, push once (Netlify credits).
