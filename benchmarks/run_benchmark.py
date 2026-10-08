"""
TrustGuard Benchmark — how accurate are the detectors on images they have never seen?

Dataset: OpenRL/DeepFakeFace (HuggingFace)
  - real:  photos of real people (IMDB-WIKI)
  - fake:  faces made by 3 different generators (Stable Diffusion text2img,
           Stable Diffusion inpainting, InsightFace face swap)
  The deepfake model (dima806/deepfake_vs_real_image_detection) was trained on a
  different Kaggle dataset, so this tests whether it works on NEW kinds of fakes.

Run from the project root:
    venv\\Scripts\\python -m benchmarks.run_benchmark            (100 real + 99 fake)
    venv\\Scripts\\python -m benchmarks.run_benchmark --n 300    (bigger sample)

It downloads only the sampled images (~10MB) into datasets/deepfakeface/ and writes
benchmarks/results.json + benchmarks/RESULTS.md.
"""

import argparse
import json
import random
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "datasets" / "deepfakeface"
REPO = "datasets/OpenRL/DeepFakeFace"
FAKE_SOURCES = ["text2img", "inpainting", "insight"]


# ── Step 1: download a random sample ────────────────────────

def download_sample(n_real: int, seed: int = 42) -> dict:
    """Download n_real real images + about the same number of fakes (split across generators).
    Reads the remote zip files directly, so only the chosen images are downloaded."""
    from huggingface_hub import HfFileSystem

    fs = HfFileSystem()
    rng = random.Random(seed)  # fixed seed = same images every run (reproducible)
    plan = {"wiki": n_real, **{src: n_real // len(FAKE_SOURCES) for src in FAKE_SOURCES}}
    samples = {}

    for source, count in plan.items():
        out_dir = DATA_DIR / source
        existing = sorted(out_dir.glob("*.jpg")) if out_dir.exists() else []
        if len(existing) >= count:
            samples[source] = existing[:count]
            continue

        print(f"Downloading {count} images from {source}.zip ...")
        out_dir.mkdir(parents=True, exist_ok=True)
        with fs.open(f"{REPO}/{source}.zip", "rb", block_size=256 * 1024) as f:
            z = zipfile.ZipFile(f)
            members = [m for m in z.infolist() if m.filename.endswith(".jpg")]
            chosen = rng.sample(members, count)
            paths = []
            for m in chosen:
                path = out_dir / Path(m.filename).name
                path.write_bytes(z.read(m))
                paths.append(path)
        samples[source] = paths

    return samples


# ── Step 2: run the detectors ───────────────────────────────

def run(samples: dict) -> dict:
    from backend.core.deepfake_detector import DeepfakeDetector
    from backend.core.liveness_detector import LivenessDetector

    deepfake = DeepfakeDetector()  # local model = same model the live API uses
    liveness = LivenessDetector()

    rows = []
    for source, paths in samples.items():
        is_fake = source != "wiki"
        for path in paths:
            df = deepfake.predict_image(str(path))
            lv = liveness.detect_liveness(str(path))
            rows.append({
                "file": f"{source}/{path.name}",
                "source": source,
                "label": "FAKE" if is_fake else "REAL",
                "fake_prob": df["probabilities"]["fake"],
                "predicted": "FAKE" if df["is_deepfake"] else "REAL",
                "liveness_score": lv["liveness_score"],
                "face_detected": lv["checks"]["face_detected"],
            })
        print(f"  {source}: {len(paths)} images done")
    return rows


# ── Step 3: score it ────────────────────────────────────────

def summarize(rows: list) -> dict:
    real = [r for r in rows if r["label"] == "REAL"]
    fake = [r for r in rows if r["label"] == "FAKE"]

    true_pos = sum(r["predicted"] == "FAKE" for r in fake)    # fakes caught
    false_neg = len(fake) - true_pos                          # fakes missed
    false_pos = sum(r["predicted"] == "FAKE" for r in real)   # real people wrongly flagged
    true_neg = len(real) - false_pos

    def pct(a, b):
        return round(100 * a / b, 1) if b else 0.0

    # AUC = chance a random fake gets a higher fake-score than a random real photo.
    # 0.5 = coin flip, 1.0 = perfect. Unlike accuracy, it doesn't depend on the threshold.
    fake_scores, real_scores = [r["fake_prob"] for r in fake], [r["fake_prob"] for r in real]
    auc = sum((f > r) + 0.5 * (f == r) for f in fake_scores for r in real_scores) / (len(fake) * len(real))

    summary = {
        "images": len(rows),
        "real": len(real),
        "fake": len(fake),
        "deepfake": {
            "accuracy": pct(true_pos + true_neg, len(rows)),
            "auc": round(auc, 3),
            "fakes_caught_pct": pct(true_pos, len(fake)),          # recall
            "fakes_missed_pct": pct(false_neg, len(fake)),         # false negative rate
            "real_wrongly_flagged_pct": pct(false_pos, len(real)), # false positive rate
            "by_generator": {
                src: pct(sum(r["predicted"] == "FAKE" for r in rows if r["source"] == src),
                         sum(r["source"] == src for r in rows))
                for src in FAKE_SOURCES
            },
        },
        "liveness_on_real_photos": {
            # These are genuine photos, not live selfies or print/screen attacks, so this is
            # only a rough "does liveness reject normal faces?" check — not a spoof benchmark.
            "face_detected_pct": pct(sum(r["face_detected"] for r in real), len(real)),
            "scored_live_pct": pct(sum(r["liveness_score"] >= 0.7 for r in real), len(real)),
            "avg_score": round(sum(r["liveness_score"] for r in real) / len(real), 3) if real else 0,
        },
    }
    return summary


def write_report(summary: dict, rows: list, seconds: float):
    out = Path(__file__).parent
    (out / "results.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))

    d, lv = summary["deepfake"], summary["liveness_on_real_photos"]
    gen = "\n".join(f"| {src} | {p}% |" for src, p in d["by_generator"].items())
    md = f"""# Benchmark Results

Dataset: [OpenRL/DeepFakeFace](https://huggingface.co/datasets/OpenRL/DeepFakeFace) — {summary['real']} real + {summary['fake']} fake face images,
random sample (seed 42). The deepfake model was **not** trained on this dataset.
Reproduce: `python -m benchmarks.run_benchmark` (took {seconds:.0f}s on CPU).

## Deepfake detector

| Metric | Result |
|---|---|
| Accuracy | **{d['accuracy']}%** |
| AUC (0.5 = guessing, 1.0 = perfect) | {d['auc']} |
| Fakes caught | {d['fakes_caught_pct']}% |
| Fakes missed (false negatives) | {d['fakes_missed_pct']}% |
| Real people wrongly flagged (false positives) | {d['real_wrongly_flagged_pct']}% |

Fakes caught, by generator:

| Generator | Caught |
|---|---|
{gen}

## Liveness detector (sanity check only)

On the {summary['real']} genuine face photos: face found in {lv['face_detected_pct']}%, scored LIVE (≥ 0.7) in {lv['scored_live_pct']}%, average score {lv['avg_score']}.
These are ordinary photos, not live selfies or print/screen attacks, so this only shows how often liveness
rejects normal faces. A real spoof benchmark needs a presentation-attack dataset.
"""
    (out / "RESULTS.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100, help="number of real images (fakes ≈ same)")
    args = parser.parse_args()

    start = time.time()
    samples = download_sample(args.n)
    rows = run(samples)
    write_report(summarize(rows), rows, time.time() - start)
