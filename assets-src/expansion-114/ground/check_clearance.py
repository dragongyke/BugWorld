"""Inspect non-adjacent grasshopper wing/leg triangle intersections on actual reimported skin."""
from pathlib import Path
import json
import bpy
from mathutils.bvhtree import BVHTree

out=Path(__file__).resolve().parents[1]/'grasshopper'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(out.parents[2]/'app/src/main/assets/v3/models/grasshopper.glb'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
rig.animation_data.action=None;tracks=rig.animation_data.nla_tracks
objs=[o for o in scene.objects if o.type=='MESH' and o.visible_get() and not o.hide_render]
def select(clip,t):
    tr=next(tr for tr in tracks if tr.name==clip)
    for track in tracks:track.mute=track!=tr
    s=tr.strips[0];f=s.frame_start+t*(s.frame_end-s.frame_start)
    scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
def trees():
    parts={};dg=bpy.context.evaluated_depsgraph_get();minz=float('inf')
    for obj in objs:
        o=obj.evaluated_get(dg);m=o.to_mesh();m.calc_loop_triangles()
        groups=[obj.vertex_groups[v.groups[0].group].name if v.groups else '' for v in m.vertices]
        minz=min(minz,min((o.matrix_world@v.co).z for v in m.vertices))
        for tri in m.loop_triangles:
            ids=tri.vertices[:];name=groups[ids[0]]
            if not (name.startswith(('Tegmen','Fan')) or name.startswith(('L3','R3'))):continue
            points,faces=parts.setdefault(name,([],[]));start=len(points)
            points.extend(o.matrix_world@m.vertices[i].co for i in ids);faces.append((start,start+1,start+2))
        o.to_mesh_clear()
    return {name:BVHTree.FromPolygons(points,faces,all_triangles=True) for name,(points,faces) in parts.items()},minz
records=[]
for clip in ['idle','walk','hop','takeoff','flight','touch','perch']:
    tr=next(tr for tr in tracks if tr.name==clip);strip=tr.strips[0]
    frames=round(strip.frame_end-strip.frame_start)
    phases=[i/frames for i in range(frames+1)]
    for t in phases:
        select(clip,t);bvh,minz=trees();hits={}
        for s,tag in [(-1,'R'),(1,'L')]:
            for a in [f'Tegmen {s}']+[f'Fan {s} sector {j}' for j in range(3)]:
                for b in [f'{tag}3 femur',f'{tag}3 tibia',f'{tag}3 tarsus']:
                    crossings=bvh[a].overlap(bvh[b])
                    if crossings:hits[f'{a} / {b}']=len(crossings)
        records.append({'clip':clip,'phase':t,'lowestVertexAboveRestPlaneMeters':minz,'wingHindLegCrossings':hits})
        print('CLEARANCE',clip,t,hits,flush=True)
(out/'wing-leg-clearance.json').write_text(json.dumps(records,indent=2))
