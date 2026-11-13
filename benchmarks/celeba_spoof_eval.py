"""
Check the production liveness detector on FULL-SIZE photos (CelebA-Spoof, label live / spoof).
CASIA frames are tiny face crops; these are normal photos with background, like a webcam selfie.
Spoofs here are prints, phone/screen replays and masks. Reads only a few row groups from the
remote parquet files (about 350 MB), keeps the images in memory, and writes
benchmarks/celeba_spoof_scores.csv. Nothing here is tuned: model + threshold are as shipped.

    venv/Scripts/python -m benchmarks.celeba_spoof_eval
"""

import io
import random
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from huggingface_hub import HfApi, HfFileSystem

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.core.liveness_detector import LivenessDetector  # noqa: E402

REPO = "Ar4ikov/celebA_spoof"
N_SHARDS, GROUPS_PER_SHARD = 4, 2


def main():
    files = sorted(s.rfilename for s in HfApi().dataset_info(REPO).siblings if "test-" in s.rfilename)
    shards = random.Random(7).sample(files, N_SHARDS)
    fs = HfFileSystem()
    detector = LivenessDetector()
    rows = []
    for f in shards:
        pf = pq.ParquetFile(fs.open(f"datasets/{REPO}/{f}"))
        classes = [pf.read_row_group(g, columns=["Class"]).column("Class").to_pylist() for g in range(pf.metadata.num_row_groups)]
        # the groups with the most real faces (spoof-only groups would tell us nothing about false rejects)
        best = sorted(range(len(classes)), key=lambda g: -classes[g].count("live"))[:GROUPS_PER_SHARD]
        for g in best:
            tb = pf.read_row_group(g, columns=["Filepath", "Class"])
            for img, cls in zip(tb.column("Filepath").to_pylist(), tb.column("Class").to_pylist()):
                bgr = cv2.imdecode(np.frombuffer(img["bytes"], np.uint8), cv2.IMREAD_COLOR)
                if bgr is None:
                    continue
                r = detector.detect_liveness(bgr)
                c = r["checks"]
                bb = c["face_bbox"]
                rows.append({"shard": f[-30:-8], "is_real": int(cls == "live"), "face_detected": int(c["face_detected"]),
                             "face_w": bb["width_pct"] if bb else 0, "face_h": bb["height_pct"] if bb else 0,
                             "img_w": bgr.shape[1], "img_h": bgr.shape[0],
                             "p_live": c["model_live_probability"], "score": r["liveness_score"]})
            print(f"{f[-30:-8]} group {g}: {len(rows)} images so far", flush=True)
    pd.DataFrame(rows).to_csv(ROOT / "benchmarks" / "celeba_spoof_scores.csv", index=False)


if __name__ == "__main__":
    main()
