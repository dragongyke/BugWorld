"""Extract neutral surface detail that survives replacing the GLB's example colors with player paint."""
import io
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "scripts"))
from audit_stage_glb import read_glb

assets = root / "app/src/main/assets/v3"
for slug in ("dragonfly", "honeybee", "ant", "grasshopper"):
    _, glb, blob = read_glb(assets / "models" / f"{slug}.glb")
    mat = next(m for m in glb["materials"] if m["name"] == f"Paper_{slug}")
    tex = mat["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    image = glb["images"][glb["textures"][tex]["source"]]
    view = glb["bufferViews"][image["bufferView"]]
    start = view.get("byteOffset", 0)
    source = Image.open(io.BytesIO(blob[start:start + view["byteLength"]])).convert("L")
    mask = Image.open(assets / "templates" / f"{slug}-mask.png").getchannel("R")
    source = source.resize(mask.size, Image.Resampling.LANCZOS)
    luma = np.asarray(source, dtype=np.float32)
    broad = np.asarray(source.filter(ImageFilter.GaussianBlur(6)), dtype=np.float32)
    signal = np.clip(128 + (luma-broad)*0.58, 104, 148).round().astype(np.uint8)
    signal[np.asarray(mask) == 0] = 128
    Image.fromarray(signal).save(assets / "templates" / f"{slug}-detail.png", optimize=True)
