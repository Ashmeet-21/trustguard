"""
Real-webcam ACCEPTANCE test of the head-turn challenge (R1). Same flow and same rule as the app:
a front photo, then ~1.5 s later a turned photo, scored with head_turn_passes() from the server code.
Do NOT change thresholds based on a run of this script (that would make it tuning data again).

Modes (10 trials each, you get a prompt before every photo):
  venv\\Scripts\\python -m benchmarks.headturn_test left          # live: straight, then turn to YOUR left shoulder
  venv\\Scripts\\python -m benchmarks.headturn_test right         # live: straight, then turn to YOUR right shoulder
  venv\\Scripts\\python -m benchmarks.headturn_test photo-left    # ATTACK: phone shows a straight photo, then a turned photo; server asks "left"
  venv\\Scripts\\python -m benchmarks.headturn_test photo-right   # ATTACK: same, server asks "right"
For photo modes keep your own face out of view and use a photo of a face (try a straight one and a turned one).

The frame is flipped left-right before measuring, because the app's camera preview and snapshot are mirrored.
Frames are saved in datasets/webcam_test/ (gitignored).
"""

import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).parent.parent
OUT = ROOT / "datasets" / "webcam_test"
sys.path.insert(0, str(ROOT))

from backend.core.liveness_detector import LivenessDetector  # noqa: E402
from backend.core.session_orchestrator import FRONT_MAX_YAW, TURN_MIN_YAW, head_turn_passes  # noqa: E402

TRIALS = 10


def snap(cap, path):
    for _ in range(5):  # drop stale buffered frames
        cap.read()
    ok, frame = cap.read()
    if not ok:
        return None
    frame = cv2.flip(frame, 1)  # mirror, same as the app
    cv2.imwrite(str(path), frame)
    return frame


def main(mode):
    attack = mode.startswith("photo")
    asked = mode.split("-")[-1]
    OUT.mkdir(parents=True, exist_ok=True)
    detector = LivenessDetector()
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    for _ in range(20):  # let the camera adjust exposure
        cap.read()
    print(f"\nMode: {mode} (server asks '{asked}'). First trial in {20 if attack else 6} seconds.", flush=True)
    time.sleep(20 if attack else 6)
    passed = 0
    for i in range(TRIALS):
        print(f"\nTrial {i + 1}/{TRIALS}", flush=True)
        print("  >> " + ("SHOW a STRAIGHT photo" if attack else "LOOK STRAIGHT at the camera"), flush=True)
        time.sleep(3)
        front = snap(cap, OUT / f"pair_{mode}_{i + 1:02d}_front.jpg")
        print("  >> " + ("SHOW a TURNED photo (tilt it)" if attack else f"TURN to your {asked.upper()} shoulder NOW"), flush=True)
        time.sleep(1.5)
        turned = snap(cap, OUT / f"pair_{mode}_{i + 1:02d}_turn.jpg")
        if front is None or turned is None:
            print("  camera read failed")
            break
        fy, ty = detector.head_yaw(front), detector.head_yaw(turned)
        if fy is None or ty is None:
            print(f"  front={fy} turn={ty} -> no face -> FAIL")
            ok = False
        else:
            ok, reason = head_turn_passes(asked, fy, ty)
            print(f"  front={fy:+.3f} turn={ty:+.3f} change={ty - fy:+.3f} -> {'PASS' if ok else 'FAIL (' + reason + ')'}", flush=True)
        passed += ok
        time.sleep(3)  # relax back
    cap.release()
    if attack:
        print(f"\n{mode}: attack PASSED {passed}/{TRIALS} (lower is better)")
    else:
        print(f"\n{mode}: live PASSED {passed}/{TRIALS} (target >= 9/10)")
    print(f"(rule: front |yaw| <= {FRONT_MAX_YAW}, change >= {TURN_MIN_YAW}; left is NEGATIVE, right is POSITIVE)")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("left", "right", "photo-left", "photo-right"):
        sys.exit(__doc__)
    main(sys.argv[1])
