"""Clean GLB round trip. Render selected actual poses and measure skin/UV output."""
from pathlib import Path
import argparse
import json
import sys
import bpy
import numpy as np
from mathutils import Vector

p=argparse.ArgumentParser()
p.add_argument('--species',required=True);args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
kind=args.species
out=Path(__file__).resolve().parents[1]/kind
runtime=out.parents[2]/'app/src/main/assets/v3'
poses=([('idle',0,'rest'),('walk',.15,'walk'),('explore',.27,'probe'),('groom',.48,'groom'),('touch',.28,'touch')]
       if kind=='ant' else [('idle',0,'rest'),('hop',.17,'crouch'),('hop',.5,'spring'),('hop',.88,'land'),
                            ('takeoff',.8,'takeoff'),('flight',.13,'flight'),('perch',.49,'perch')])
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(runtime/f'models/{kind}.glb'))
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=3
rig=next(o for o in scene.objects if o.type=='ARMATURE')
objs=[o for o in scene.objects if o.type=='MESH' and o.visible_get() and not o.hide_render]
tracks=list(rig.animation_data.nla_tracks);rig.animation_data.action=None
report={'source':f'app/src/main/assets/v3/models/{kind}.glb','triangles':sum(len(p.vertices)-2 for o in objs for p in o.data.polygons),
        'meshNames':[o.name for o in objs],'bones':list(rig.pose.bones.keys()),'clips':{},'renders':{}}
def select(clip,fraction):
    tr=next(t for t in tracks if t.name==clip)
    for t in tracks:t.mute=t!=tr
    strip=tr.strips[0];f=strip.frame_start+(strip.frame_end-strip.frame_start)*fraction
    scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
    return f
def bounds():
    dg=bpy.context.evaluated_depsgraph_get(); vs=[]
    for obj in objs:
        o=obj.evaluated_get(dg);m=o.to_mesh();q=np.empty(3*len(m.vertices),dtype='float32');m.vertices.foreach_get('co',q)
        a=np.array(o.matrix_world);vs.append(q.reshape(-1,3)@a[:3,:3].T+a[:3,3]);o.to_mesh_clear()
    v=np.concatenate(vs);return v.min(axis=0),v.max(axis=0)
for tr in tracks:
    s=tr.strips[0];report['clips'][tr.name]=round((s.frame_end-s.frame_start)/24,4)
select('idle',0)
l,h=bounds();restspan=max(h-l);center=Vector((h+l)*.5)
report['restBoundsBlender']=[l.tolist(),h.tolist()]
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    if any(d.type=='OPTIX' for d in prefs.devices):
        for d in prefs.devices:d.use=d.type=='OPTIX'
        scene.cycles.device='GPU'
except RuntimeError:pass
scene.world=bpy.data.worlds.new('Quiet garden studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.25,.29,.24,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.42
floor_mat=bpy.data.materials.new('Muted olive studio ground');floor_mat.use_nodes=True
floor_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.16,.18,.12,1)
bpy.ops.mesh.primitive_plane_add(size=restspan*200,location=(0,0,-.0002))
floor=bpy.context.object;floor.data.materials.append(floor_mat)
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';camera.data.clip_start=.001
scene.camera=camera
for direction,power,size in [((.50,.56,1.25),26,.98),((-.8,-1.3,1.4),26,.90)]:
    bpy.ops.object.light_add(type='AREA',location=center+Vector(direction)*restspan)
    lamp=bpy.context.object;lamp.data.energy=power*restspan**2;lamp.data.shape='DISK';lamp.data.size=size*restspan
    lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
for clip,t,label in poses:
    f=select(clip,t);l,h=bounds()
    direction=Vector((.18,1.65,.48)) if kind=='ant' else Vector((.12,1.65,.40))
    # A second, elevated view makes deployed tegmina/fans and asymmetry visible.
    if label in ('flight','takeoff'):direction=Vector((.42,1.1,1.52))
    if label=='groom':direction=Vector((.47,1.40,.54))
    aim=Vector((h+l)*.5) if label in ('flight','takeoff','spring') else center.copy()
    camera.location=aim+direction*restspan
    camera.rotation_euler=(aim-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=max(restspan*1.16,max(h-l)*(1.83 if label in ('flight','takeoff') else 1.16))
    scene.render.resolution_x=800 if label=='rest' else 440;scene.render.resolution_y=490 if label=='rest' else 270
    scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.render.filepath=str(out/(label+'.png'));bpy.ops.render.render(write_still=True)
    report['renders'][label]={'clip':clip,'frame':f,'bounds':[l.tolist(),h.tolist()]}
    print('CHECKED',kind,label,flush=True)
(out/'roundtrip.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
