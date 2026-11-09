"""Read the real reviewed HDR in Blender, preserving linear radiance."""
import argparse,sys,json
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True)
out=p.parse_args(sys.argv[sys.argv.index('--')+1:]).output_dir
out.mkdir(parents=True,exist_ok=True)
image=bpy.data.images.load(str(ROOT/'assets-src/emerald-forest-v2/sources/forest_slope_4k.exr'))
image.scale(1024,512)
pixels=np.empty(1024*512*4,dtype=np.float32);image.pixels.foreach_get(pixels)
linear=pixels.reshape(512,1024,4)[::-1,:,:3].copy()
assert np.isfinite(linear).all() and linear.max()>1
np.save(out/'forest-hdr.npy',linear)
(out/'hdr-report.json').write_text(json.dumps(dict(size=[1024,512],minimum=float(linear.min()),maximum=float(linear.max()))))
print('HDR_LINEAR',linear.shape,float(linear.max()))
