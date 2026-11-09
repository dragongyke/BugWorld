"""Render an authored review .blend with a verified OptiX device; no asset mutation."""
import argparse
import sys
from pathlib import Path
import bpy

p=argparse.ArgumentParser()
p.add_argument('--output-dir',required=True)
p.add_argument('--image',default='garden-actual.png')
p.add_argument('--resolution',type=int,default=1440)
p.add_argument('--samples',type=int,default=64)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
enabled=[]
for device in prefs.devices:
    device.use=device.type=='OPTIX'
    if device.use:enabled.append(device.name)
assert enabled,'No OptiX device; do not silently change review renderer.'
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.device='GPU'
sc.cycles.samples=args.samples;sc.cycles.use_denoising=True
sc.render.resolution_x=args.resolution;sc.render.resolution_y=round(args.resolution*9/16)
sc.render.resolution_percentage=100;sc.render.filepath=str(Path(args.output_dir)/args.image)
print('Review render GPU:',enabled,flush=True)
bpy.ops.render.render(write_still=True)
