"""Fresh GLB import and paired rendering, using identical lights/cameras and clip times."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

p=argparse.ArgumentParser()
p.add_argument('--output-dir',required=True)
p.add_argument('--source-dir',type=Path)
p.add_argument('--candidate-dir',type=Path)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[1]
records=[]

for kind in ('butterfly','beetle','ladybug','caterpillar'):
    for variant in ('source','batched'):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        path=root/(f'assets-src/v3-review/{kind}/{kind}.glb' if variant=='source'
                   else f'assets-src/insects-batched/{kind}.glb')
        if variant=='source' and args.source_dir: path=args.source_dir/f'{kind}.glb'
        if variant=='batched' and args.candidate_dir: path=args.candidate_dir/f'{kind}.glb'
        bpy.ops.import_scene.gltf(filepath=str(path))
        scene=bpy.context.scene
        # glTF importer also creates a hidden mesh for bone display; never frame it.
        meshes=[o for o in scene.objects if o.type=='MESH' and not o.hide_render and o.visible_get()]
        bounds=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
        low=Vector(tuple(min(v[i] for v in bounds) for i in range(3)))
        high=Vector(tuple(max(v[i] for v in bounds) for i in range(3)))
        center=(high+low)*.5;span=max(high-low)
        bpy.ops.object.camera_add(location=center+Vector((1.4,-2.0,1.4))*span)
        camera=bpy.context.object;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.type='ORTHO';camera.data.ortho_scale=span*1.5;camera.data.clip_end=span*30
        scene.camera=camera
        scene.world=bpy.data.worlds.new('comparison-world');scene.world.use_nodes=True
        scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.18,.22,1)
        scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
        lights=[]
        for direction,power,size in [((1,-2,3),900,3),((-2,0,1),500,3)]:
            bpy.ops.object.light_add(type='AREA',location=center+Vector(direction)*span)
            light=bpy.context.object;light.data.energy=power*span*span;light.data.shape='DISK';light.data.size=size*span
            light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
            lights.append((light,direction,power,size))
        scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=False;scene.cycles.seed=17
        prefs=bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type='OPTIX';prefs.get_devices()
        devices=[d for d in prefs.devices if d.type=='OPTIX']
        assert devices,'OptiX GPU required'
        for device in prefs.devices:device.use=device.type=='OPTIX'
        scene.cycles.device='GPU'
        scene.render.resolution_x=480;scene.render.resolution_y=480;scene.render.resolution_percentage=100
        scene.render.image_settings.file_format='PNG'
        rigs=[o for o in scene.objects if o.type=='ARMATURE']
        assert len(rigs)==1
        rig=rigs[0]
        tracks=list(rig.animation_data.nla_tracks)
        assert len(tracks)==5,(kind,[t.name for t in tracks])
        clip_word='caterpillar_crawl' if kind=='caterpillar' else ('butterfly_fly' if kind=='butterfly' else 'flight')
        moving=next(t for t in tracks if clip_word in t.name)
        rest=next(t for t in tracks if ('idle' in t.name))
        rig.animation_data.action=None
        for pose,track in [('idle',rest),('moving',moving)]:
            for t in tracks:t.mute=t!=track
            strip=track.strips[0]
            frame=strip.frame_start+(strip.frame_end-strip.frame_start)*.35
            scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
            # Fit the evaluated skinned pose, not un-deformed import bounds.
            depsgraph=bpy.context.evaluated_depsgraph_get()
            evaluated=[o.evaluated_get(depsgraph) for o in meshes]
            positions=[]
            for obj in evaluated:
                mesh=obj.to_mesh()
                coords=np.empty(len(mesh.vertices)*3,dtype=np.float32)
                mesh.vertices.foreach_get('co',coords)
                matrix=np.array(obj.matrix_world)
                positions.append(coords.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3])
                obj.to_mesh_clear()
            vertices=np.concatenate(positions)
            low=Vector(vertices.min(axis=0));high=Vector(vertices.max(axis=0))
            center=(high+low)*.5;span=max(high-low)
            camera.location=center+Vector((1.4,-2.0,1.4))*span
            camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
            camera.data.ortho_scale=span*1.35;camera.data.clip_start=span*.001;camera.data.clip_end=span*30
            for light,direction,power,size in lights:
                light.location=center+Vector(direction)*span
                light.data.energy=power*span*span;light.data.size=size*span
                light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
            name=f'{kind}-{pose}-{variant}.png'
            scene.render.filepath=str(out/name)
            bpy.ops.render.render(write_still=True)
            records.append({'species':kind,'variant':variant,'pose':pose,'clip':track.name,
                            'frame':frame,'span':span,'meshes':len(meshes),'image':name,'source':str(path)})
            print('VERIFIED_RENDER',name,flush=True)
        if variant=='batched':
            bpy.ops.wm.save_as_mainfile(filepath=str(out/f'{kind}-inspection.blend'))
(out/'render-report.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
