"""
Real-webcam check of the liveness model (CASIA frames are tiny crops; this uses full webcam frames).

Phase 1 - you look at the camera:            venv\Scripts\python -m benchmarks.webcam_test live
Phase 2 - hold a phone showing a photo of
          your face (or a printed photo):    venv\Scripts\python -m benchmarks.webcam_test spoof

Takes 10 shots, 4 seconds apart. For 'spoof' ONLY the phone/print may show a face: keep your own
face out of the camera view and tilt / move the phone between shots.
Frames are saved in datasets/webcam_test/ (gitignored, stays on this laptop).
"""

import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).parent.parent
OUT = ROOT / "datasets" / "webcam_test"
sys.path.insert(0, str(ROOT))

from backend.core.liveness_detector import LivenessDetector  # noqa: E402

SHOTS, GAP = 10, 4


def main(mode):
    OUT.mkdir(parents=True, exist_ok=True)
    detector = LivenessDetector()
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    for _ in range(20):  # let the camera adjust exposure
        cap.read()
    wait = 20 if mode == "spoof" else 8  # spoof needs time to set up the phone
    print(f"\nMode: {mode}. First shot in {wait} seconds - get ready.", flush=True)
    time.sleep(wait)
    passed = 0
    for i in range(SHOTS):
        for _ in range(5):  # drop stale buffered frames
            cap.read()
        ok, frame = cap.read()
        if not ok:
            print("camera read failed")
            break
        cv2.imwrite(str(OUT / f"{mode}_{i + 1:02d}.jpg"), frame)
        r = detector.detect_liveness(frame)
        c = r["checks"]
        passed += r["is_live"]
        bb = c["face_bbox"]  # where the face is: lets us see WHICH face was scored
        where = (f"face x={(bb['x_min'] + bb['x_max']) / 2:.2f} y={(bb['y_min'] + bb['y_max']) / 2:.2f} "
                 f"w={bb['width_pct']:.2f}") if bb else "no face"
        print(f"shot {i + 1:2d}: {where:30} P(live)={c['model_live_probability']:.3f} "
              f"score={r['liveness_score']:.2f} -> {r['classification']} ({r['risk_level']})", flush=True)
        time.sleep(GAP)
    cap.release()
    print(f"\n{mode}: {passed}/{SHOTS} classified LIVE")
    print("Good result: live -> most LIVE, spoof -> most SPOOF.")


if __name__ == "__main__":
    main(sys.argv[1])
