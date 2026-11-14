"""
SIMULATED photo-tilt attack on the head-turn check (no webcam needed).
Attacker holds up a straight photo (front shot), then tilts the same photo like a phone turned
on its vertical axis (turn shot). We fake the tilt with a perspective warp, then score both shots
with the SAME head_turn_passes() the server uses. Threshold is FROZEN: do not tune on this.

This is a simulation, not a real phone on a real camera. It does NOT test the case where the
attacker has a photo of an already-turned head (that passes by design, see CLAUDE.md).

Run: venv\\Scripts\\python -m benchmarks.photo_tilt_attack
"""

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.core.liveness_detector import LivenessDetector  # noqa: E402
from backend.core.session_orchestrator import FRONT_MAX_YAW, TURN_MIN_YAW, head_turn_passes  # noqa: E402

PHOTOS = ROOT / "datasets" / "deepfakeface" / "wiki"  # real photos of people the project never tuned on
ANGLES = [15, 25, 35, 45]  # degrees the "phone" is turned


def tilt(img, degrees, side):
    """Perspective warp: one vertical edge looks farther away (smaller), as if turned on a vertical axis."""
    h, w = img.shape[:2]
    a = np.radians(degrees)
    narrow = 1 - 0.5 * np.sin(a)  # far edge height shrinks
    squeeze = (1 - np.cos(a)) / 2 * w  # image gets narrower from the side
    far = (h * (1 - narrow)) / 2
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    if side == "right-far":
        dst = np.float32([[squeeze, 0], [w - squeeze, far], [w - squeeze, h - far], [squeeze, h]])
    else:
        dst = np.float32([[squeeze, far], [w - squeeze, 0], [w - squeeze, h], [squeeze, h - far]])
    return cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (w, h))


def main():
    detector = LivenessDetector()
    paths = sorted(PHOTOS.glob("*.jpg"))
    fronts = []
    for p in paths:
        img = cv2.imread(str(p))
        yaw = detector.head_yaw(img) if img is not None else None
        if yaw is not None and abs(yaw) <= FRONT_MAX_YAW:
            fronts.append((img, yaw))
    print(f"{len(paths)} photos, {len(fronts)} usable as a straight front shot (face found, |yaw| <= {FRONT_MAX_YAW})")
    print(f"rule: change >= {TURN_MIN_YAW} in the asked direction. Lower attack pass rate is better.\n")

    print("angle  asked  side        passed   no-face")
    total = 0
    total_pass = 0
    for angle in ANGLES:
        for side in ("right-far", "left-far"):
            for asked in ("left", "right"):
                passed = noface = 0
                for img, fy in fronts:
                    ty = detector.head_yaw(tilt(img, angle, side))
                    if ty is None:
                        noface += 1
                        continue
                    passed += head_turn_passes(asked, fy, ty)[0]
                print(f"{angle:>4}   {asked:<5}  {side:<10}  {passed:>3}/{len(fronts):<3}  {noface:>3}")
                total += len(fronts)
                total_pass += passed
    print(f"\nALL tilts: attack passed {total_pass}/{total} = {100 * total_pass / max(total, 1):.1f}%")


if __name__ == "__main__":
    main()
