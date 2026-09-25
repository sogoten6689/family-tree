import os
import pathlib
import time


def check_line_direction(baseline_seg):
    """Check if the lines are oriented top to bottom, if not inverse their direction.

    Adapted for kraken>=5.x API where blla.segment() returns a
    kraken.containers.Segmentation object (attribute access) instead of
    the older dict-based API (subscript access) that the original
    demo/chat_models_demo.py from this repo was written against.
    """
    for line in baseline_seg.lines:
        if line.baseline[0][1] > line.baseline[-1][1]:
            line.baseline = list(reversed(line.baseline))
    return baseline_seg


if __name__ == '__main__':

    try:
        from kraken import blla, rpred
        from kraken.lib import vgsl, models
    except ImportError:
        print("Install kraken OCR engine to run this script: https://github.com/mittagessen/kraken#installation.")
        exit(1)

    import torch
    from PIL import Image

    torch.set_num_threads(1)

    cwd = pathlib.Path.cwd()
    models_dir = cwd / "models"
    test_dir = cwd / "test"
    seg_model_path = models_dir / "chat_seg.mlmodel"
    rec_model_path = models_dir / "chat_rec.mlmodel"

    assert seg_model_path.exists()
    assert rec_model_path.exists()

    print(f"Loading segmentation model from {seg_model_path} ...")
    seg_model = vgsl.TorchVGSLModel.load_model(seg_model_path)
    print(f"Loading recognition model from {rec_model_path} ...")
    rec_model = models.load_any(rec_model_path)

    for img_path in sorted(test_dir.glob("*.png")):
        print(f"\n=== {img_path.name} ===")
        t0 = time.time()
        img = Image.open(img_path)
        img = img.convert("L")
        img = img.point(lambda x: 0 if x < 128 else 255, "1")

        t1 = time.time()
        baseline_seg = blla.segment(img, text_direction="vertical-rl", model=seg_model)
        t2 = time.time()
        print(f"  segmentation: {len(baseline_seg.lines)} lines found in {t2 - t1:.1f}s")

        baseline_seg = check_line_direction(baseline_seg)

        pred_it = rpred.rpred(rec_model, img, baseline_seg)
        n = 0
        for record in pred_it:
            n += 1
            print(f"  line {n:02d}: {record.prediction}")
        t3 = time.time()
        print(f"  recognition: {n} lines transcribed in {t3 - t2:.1f}s (total {t3 - t0:.1f}s for this image)")

    print("\nDone!")
