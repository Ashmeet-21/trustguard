# Benchmark Results

Model: `buildborderless/CommunityForensics-DeepfakeDet-ViT` · Dataset: [OpenRL/DeepFakeFace](https://huggingface.co/datasets/OpenRL/DeepFakeFace) — 100 real + 99 fake face images,
random sample (seed 42). The deepfake model was **not** trained on this dataset.
How this model was chosen: [MODEL_COMPARISON.md](MODEL_COMPARISON.md).
Reproduce: `python -m benchmarks.run_benchmark` (took 30s on CPU).

## Deepfake detector

| Metric | Result |
|---|---|
| Accuracy | **79.9%** |
| AUC (0.5 = guessing, 1.0 = perfect) | 0.882 |
| Fakes caught | 59.6% |
| Fakes missed (false negatives) | 40.4% |
| Real people wrongly flagged (false positives) | 0.0% |

Fakes caught, by generator:

| Generator | Caught |
|---|---|
| text2img | 100.0% |
| inpainting | 75.8% |
| insight | 3.0% |

## Liveness detector (sanity check only)

On the 100 genuine face photos: face found in 83.0%, scored LIVE (≥ 0.7) in 60.0%, average score 0.656.
These are ordinary photos, not live selfies or print/screen attacks, so this only shows how often liveness
rejects normal faces. A real spoof benchmark needs a presentation-attack dataset.
