"""Package the approved store icon for Android and PICO (no artwork regeneration).

Requires NumPy and Pillow. Run from any directory with Python 3.
The two ordered PICO layers keep the existing launcher contract: a full artwork
front tile and a matching solid back tile, both with the same rounded silhouette.
"""
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deliverables/store-media-2026-11-16/BugWorld-AppIcon-1024.png"
RES = ROOT / "app/src/main/res"
SIZE = 1024


def main():
    with Image.open(SOURCE) as source:
        assert source.size == (SIZE, SIZE), "Approved icon must be 1024 square"
        artwork = source.convert("RGBA")
    assert SOURCE.stat().st_size < 4_000_000
    # Analytic signed distance for the existing 22%-radius launcher tile.
    # Positive inside; center pixels encode 255, outer pixels 0, edge 128.
    yy, xx = np.mgrid[:SIZE, :SIZE].astype(np.float32)
    radius = SIZE * .22
    qx = np.abs(xx + .5 - SIZE / 2) - (SIZE / 2 - radius)
    qy = np.abs(yy + .5 - SIZE / 2) - (SIZE / 2 - radius)
    distance = radius - (np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
                         + np.minimum(np.maximum(qx, qy), 0))
    alpha = Image.fromarray(np.uint8(np.clip(distance + .5, 0, 1) * 255))
    field = Image.fromarray(np.uint8(np.clip(128 + distance * 9, 0, 255)))
    sdf = Image.merge("RGBA", (field, field, field, alpha))
    back = Image.new("RGBA", (SIZE, SIZE), "#174E3E")
    drawable = RES / "drawable"
    for index, layer in enumerate((back, artwork)):
        layer.putalpha(alpha)
        layer.save(drawable / f"icon_3d_layer_{index}.png", optimize=True)
        sdf.save(drawable / f"icon_3d_sdf_{index}.png", optimize=True)
    # Ordinary Android entry uses the approved full-bleed image unchanged.
    target = RES / "mipmap-xxxhdpi/ic_spatial_launcher.png"
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(SOURCE.read_bytes())
    print("Packaged approved icon: Android PNG + two PICO color/SDF layers")


if __name__ == "__main__":
    main()
