"""
Export the deepfake model to ONNX so the server can run it without PyTorch or a paid API.

    venv\\Scripts\\python -m scripts.export_deepfake_onnx

Writes:
  backend/models/deepfake_vit_int8.onnx   — quantized (int8 weights), shipped with the app
  datasets/onnx/deepfake_vit_fp32.onnx     — full precision, only for comparison (gitignored)

Why: the HF Inference API needs paid credits, and PyTorch is too big for Render's free 512MB plan.
ONNX Runtime is small, and int8 quantization shrinks the weights ~4x.
"""

from pathlib import Path

import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModelForImageClassification

from backend.utils import config

ROOT = Path(__file__).parent.parent
FP32_PATH = ROOT / "datasets" / "onnx" / "deepfake_vit_fp32.onnx"
INT8_PATH = ROOT / "backend" / "models" / "deepfake_vit_int8.onnx"


class LogitsOnly(torch.nn.Module):
    """Wrap the HF model so the ONNX graph has one plain output: logits."""

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, pixel_values):
        return self.model(pixel_values=pixel_values).logits


def main():
    print(f"Loading {config.HF_IMAGE_MODEL} ...")
    model = AutoModelForImageClassification.from_pretrained(config.HF_IMAGE_MODEL).eval()
    size = model.config.image_size

    FP32_PATH.parent.mkdir(parents=True, exist_ok=True)
    INT8_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("Exporting to ONNX (fp32) ...")
    torch.onnx.export(
        LogitsOnly(model),
        (torch.randn(1, 3, size, size),),
        str(FP32_PATH),
        input_names=["pixel_values"],
        output_names=["logits"],
        dynamic_axes={"pixel_values": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
        dynamo=False,
    )

    # Only MatMul/Gemm (the transformer layers — almost all the weights). Quantizing the patch-embedding
    # Conv produces a ConvInteger node that ONNX Runtime's CPU provider can't run.
    print("Quantizing weights to int8 ...")
    # per_channel: one scale per output channel instead of per tensor — slightly better accuracy
    # on the benchmark (AUC 0.884 vs 0.883, 82.4% vs 80.9% accuracy) for the same size.
    quantize_dynamic(str(FP32_PATH), str(INT8_PATH), weight_type=QuantType.QInt8,
                     op_types_to_quantize=["MatMul", "Gemm"], per_channel=True)

    for p in (FP32_PATH, INT8_PATH):
        print(f"  {p.relative_to(ROOT)}: {p.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
