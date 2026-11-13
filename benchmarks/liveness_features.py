"""
Score CASIA-FASD frames with the liveness detector and save every check's score to CSV.

Dataset: akahana/anti-spoofing-casiafasd on HuggingFace (CASIA-FASD frames: real faces vs
printed-photo / cut-photo / video-replay attacks). Official train/test split, different people.
Tune only on 'train'. Look at 'test' once, at the end.

Run from the project root:
    venv\Scripts\python -m benchmarks.liveness_features train
    venv\Scripts\python -m benchmarks.liveness_features test
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
DATA = ROOT / "datasets" / "casia_fasd"
sys.path.insert(0, str(ROOT))

from backend.core.liveness_detector import LivenessDetector  # noqa: E402


def main(split: str):
    df = pd.read_parquet(DATA / split / "train-00000-of-00001.parquet")
    detector = LivenessDetector()
    rows = []
    for i, r in enumerate(df.itertuples()):
        path = DATA / "raw" / r.filename.lstrip("./")
        out = detector.detect_liveness(str(path))
        c = out["checks"]
        rows.append({
            "file": path.name,
            "is_real": int(r.label),  # 1 = real person, 0 = attack
            "face_detected": int(c["face_detected"]),
            "face_quality": c["face_quality_score"],
            "texture": c["texture_score"],
            "frequency": c["frequency_score"],
            "color": c["color_score"],
            "edge": c["edge_score"],
            "sharpness": c["sharpness_score"],
            "score": out["liveness_score"],
        })
        if i % 200 == 0:
            print(f"{split}: {i}/{len(df)}", flush=True)
    pd.DataFrame(rows).to_csv(ROOT / "benchmarks" / f"liveness_{split}.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1])
