"""
Score CASIA-FASD frames with two pretrained anti-spoofing ONNX models (no training, no tuning).

  minifasnet : MiniFASNetV2 (Silent-Face-Anti-Spoofing), 80x80 BGR 0-255 (NOT /255: the upstream code
               does not scale, the HF model card is wrong), 2.7x face box, live = class 1
  resnet18   : ResNet18 trained on CelebA-Spoof, 128x128 RGB 0-255, square 1.6x face box, live = output 0

Face box comes from our own MediaPipe detector. Writes benchmarks/antispoof_<split>.csv.
    venv\Scripts\python -m benchmarks.antispoof_models_eval train
    venv\Scripts\python -m benchmarks.antispoof_models_eval test     <- run once, at the end
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import pandas as pd

ROOT = Path(__file__).parent.parent
DATA = ROOT / "datasets" / "casia_fasd"
MODELS = ROOT / "datasets" / "antispoof_models"
sys.path.insert(0, str(ROOT))

from backend.core.liveness_detector import LivenessDetector  # noqa: E402


def crop_box(img, box, scale, square):
    """Crop `scale` x the face box around its centre, shifted back inside the image (no padding)."""
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if square:
        cw = ch = min(scale * max(bw, bh), h, w)
    else:  # MiniFASNet reference: keep the box shape, clamp the scale so the crop fits the image
        s = min((h - 1) / bh, (w - 1) / bw, scale)
        cw, ch = bw * s, bh * s
    left = int(round(min(max(cx - cw / 2, 0), w - cw)))
    top = int(round(min(max(cy - ch / 2, 0), h - ch)))
    return img[top:top + int(round(ch)), left:left + int(round(cw))]


def softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


def main(split):
    df = pd.read_parquet(DATA / split / "train-00000-of-00001.parquet")
    det = LivenessDetector()
    mini = ort.InferenceSession(str(MODELS / "minifasnet_v2.onnx"), providers=["CPUExecutionProvider"])
    res = ort.InferenceSession(str(MODELS / "spoof_resnet18_s1.6_int8.onnx"), providers=["CPUExecutionProvider"])
    rows = []
    for i, r in enumerate(df.itertuples()):
        path = DATA / "raw" / r.filename.lstrip("./")
        bgr = cv2.imread(str(path))
        ok, _, bb, _ = det._detect_face(bgr)
        row = {"file": path.name, "is_real": int(r.label), "face_detected": int(ok), "minifasnet": np.nan, "resnet18": np.nan}
        if ok:
            h, w = bgr.shape[:2]
            box = (bb["x_min"] * w, bb["y_min"] * h, bb["x_max"] * w, bb["y_max"] * h)
            c = cv2.resize(crop_box(bgr, box, 2.7, False), (80, 80))
            x = c.astype(np.float32).transpose(2, 0, 1)[None]
            row["minifasnet"] = float(softmax(mini.run(None, {"input": x})[0][0])[1])
            c = cv2.resize(crop_box(bgr, box, 1.6, True), (128, 128), interpolation=cv2.INTER_LINEAR)
            x = cv2.cvtColor(c, cv2.COLOR_BGR2RGB).astype(np.float32)[None]
            row["resnet18"] = float(res.run(None, {"crop": x})[0][0][0])  # P(live)
        rows.append(row)
        if i % 400 == 0:
            print(f"{split}: {i}/{len(df)}", flush=True)
    pd.DataFrame(rows).to_csv(ROOT / "benchmarks" / f"antispoof_{split}.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1])
