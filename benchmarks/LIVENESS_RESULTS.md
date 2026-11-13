# Liveness benchmark (2026-11-13)

Data: CASIA-FASD frames (HuggingFace `akahana/anti-spoofing-casiafasd`, 256x256 face crops).
Real people vs printed-photo / cut-photo / video-replay attacks. Official split, different people
in train and test. Nothing was tuned: this is the **unchanged** `LivenessDetector`, threshold 0.7.
Reproduce: `venv\Scripts\python -m benchmarks.liveness_features train|test` (writes `liveness_*.csv`).

| | train (20 people) | test (30 people) |
|---|---|---|
| frames (real / attack) | 404 / 1251 | 591 / 1817 |
| Overall score AUC | 0.525 | 0.519 |
| Real faces rejected at 0.7 | 0.2% | 0.2% |
| **Attacks accepted at 0.7** | **99.9%** | **99.8%** |
| Mean score, real / attack | 0.78 / 0.78 | 0.78 / 0.78 |

AUC per check (0.5 = coin flip), train / test:
face_quality 0.54 / 0.58, texture 0.42 / 0.33, frequency 0.54 / 0.49, color 0.41 / 0.46,
edge 0.60 / 0.68, sharpness 0.57 / 0.56.

## What this means
- The 6 hand-made checks do not separate real faces from print/replay attacks. The score is the
  same (0.78) for both, so the check passes almost every attack.
- Earlier note "liveness wrongly flags real faces" was wrong for this kind of data. `test_face.jpg`
  scored 0.148 only because no face was found in it, not because it looked fake.
- Re-weighting the 6 checks with logistic regression (train only, subject-grouped 5-fold CV) reaches
  AUC 0.69. That is the ceiling of these features; it was not shipped.
- Caveats: CASIA-FASD is old, low-resolution and pre-cropped; live webcam frames differ. Results show
  the checks are not validated, not an exact real-world error rate.

# Pretrained anti-spoof models (2026-11-13)

Same CASIA-FASD split, models used as published (no training). Script: `benchmarks/antispoof_models_eval.py`,
scores in `benchmarks/antispoof_train.csv` / `antispoof_test.csv`. Thresholds picked on train (equal-error point);
test split run once.

| Model | Train AUC | Test AUC | Test: real rejected / attacks accepted |
|---|---|---|---|
| Our 6 checks (before) | 0.525 | 0.519 | 0.2% / 99.8% |
| **MiniFASNetV2** (Silent-Face-Anti-Spoofing, 1.7 MB, Apache-2.0), threshold 0.12 | 0.978 | **0.986** | 6.3% / 6.7% |
| ResNet18 trained on CelebA-Spoof (11 MB, non-commercial), threshold 0.20 | 0.870 | 0.849 | 27.6% / 21.1% |

Notes
- MiniFASNet needs raw 0-255 pixels, not pixel/255. The HF model card says /255; that gives 0.55 AUC (everything
  scored as one class). Found on the train split by checking the raw softmax; matches upstream code.
- MiniFASNet's training data is not stated (Minivision, private), so CASIA overlap can't be ruled out. The ResNet18
  was trained on CelebA-Spoof only, so its 0.85-0.87 is the clean out-of-dataset number. Treat MiniFASNet's 0.986 as an
  upper bound until it is checked on our own webcam photos.
- CASIA frames are old, 256px face crops. Real-webcam performance is still unmeasured.
