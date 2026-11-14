# Simulated photo-tilt attack on the head-turn check (2026-11-13)

Script: `benchmarks/photo_tilt_attack.py`. Rule and threshold unchanged (front |yaw| <= 0.15, change >= 0.10), not tuned on this run.

- Photos: 100 real face photos (`datasets/deepfakeface/wiki`); 36 usable as a straight front shot (face found, |yaw| <= 0.15).
- Attack: the same straight photo, warped like a phone turned 15/25/35/45 degrees on a vertical axis, both sides, asked left and right.
- Result: attack passed **21 of 576 tries (3.6%)**. Per setting 0-3 of 36; most passes at 35-45 degrees. At 45 degrees up to 5 of 36 had no face found (counted as fail).

Limits (say these out loud):
- A perspective warp is a simulation, not a real phone on a real camera.
- Only 36 front photos, all from one dataset.
- It does NOT cover a photo of an already-turned head (that passes by design) or a replayed video.
- The live webcam acceptance run (`benchmarks/headturn_test.py`) is still not done, so the live pass rate for real users is unproven.
