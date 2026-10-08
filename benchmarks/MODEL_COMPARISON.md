# Deepfake model comparison

Same images as RESULTS.md (DeepFakeFace, seed 42), threshold 0.5. Sorted by AUC (0.5 = guessing, 1.0 = perfect).
Reproduce: `python -m benchmarks.run_benchmark --compare`

| Model | AUC | Accuracy | Fakes caught | Real wrongly flagged | text2img | inpainting | insight |
|---|---|---|---|---|---|---|---|
| `buildborderless/CommunityForensics-DeepfakeDet-ViT` | **0.882** | 79.9% | 59.6% | 0.0% | 100.0% | 75.8% | 3.0% |
| `Smogy/SMOGY-Ai-images-detector` | **0.687** | 68.3% | 72.7% | 36.0% | 93.9% | 66.7% | 57.6% |
| `haywoodsloan/ai-image-detector-deploy` | **0.685** | 58.8% | 19.2% | 2.0% | 48.5% | 6.1% | 3.0% |
| `Ateeqq/ai-vs-human-image-detector` | **0.664** | 61.3% | 58.6% | 36.0% | 87.9% | 39.4% | 48.5% |
| `prithivMLmods/Deep-Fake-Detector-v2-Model` | **0.568** | 50.3% | 96.0% | 95.0% | 90.9% | 100.0% | 97.0% |
| `umm-maybe/AI-image-detector` | **0.551** | 50.8% | 34.3% | 33.0% | 36.4% | 33.3% | 33.3% |
| `prithivMLmods/AI-vs-Deepfake-vs-Real-Siglip2` | **0.538** | 51.3% | 94.9% | 92.0% | 97.0% | 93.9% | 93.9% |
| `dima806/deepfake_vs_real_image_detection (current)` | **0.405** | 50.3% | 1.0% | 1.0% | 3.0% | 0.0% | 0.0% |
