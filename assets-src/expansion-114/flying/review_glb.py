"""Clean import of the shipped GLB. Render one hero image and each authored action."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector
slug=sys.argv[sys.argv.index('--')+1]
root=Path(__file__).resolve().parents[3]; out=root/'assets-src/expansion-114'/slug
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(root/'app/src/main/assets/v3/models'/(slug+'.glb')))
scene=bpy.context.scene; rig=next(o for o in scene.objects if o.type=='ARMATURE')
meshes=[o for o in scene.objects if o.type=='MESH' and o.name in {'Anatomy','PaperSurface'}]
assert len(meshes)==2
tracks=rig.animation_data.nla_tracks
for tr in tracks:tr.mute=True
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
scene.frame_set(1);bpy.context.view_layer.update()
def geometry():
    vals=[];graph=bpy.context.evaluated_depsgraph_get()
    for obj in meshes:
        ev=obj.evaluated_get(graph);me=ev.to_mesh()
        vals.extend(tuple(ev.matrix_world@v.co) for v in me.vertices);ev.to_mesh_clear()
    return vals
points=geometry();mn=[min(v[i] for v in points) for i in range(3)];mx=[max(v[i] for v in points) for i in range(3)]
assert mn[2]>=-.0005,(slug,mn)
assert len([p for p in rig.pose.bones if 'leg' in p.name])==6
actual={tr.name:tr.strips[0].action for tr in tracks}
assert set(actual)=={'idle','walk','takeoff','flight','touch','perch'},list(actual)
def look(ob,pt):
    ob.rotation_euler=(Vector(pt)-ob.location).to_track_quat('-Z','Y').to_euler()
dragon=slug=='dragonfly'
target=Vector((-.043,0,.024) if dragon else (-.012,0,.064))
camdata=bpy.data.cameras.new('Inspection camera');camera=bpy.data.objects.new('Inspection camera',camdata);scene.collection.objects.link(camera)
camera.location=target+Vector((-.23,-.055,.42) if dragon else (.21,-.52,.153))
look(camera,target);camdata.type='ORTHO';camdata.ortho_scale=.310 if dragon else .274
camdata.clip_start=.005;scene.camera=camera
world=bpy.data.worlds.new('Warm studio skylight');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.77,.79,.76,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.32;scene.world=world
def light(name,loc,power,color,radius):
    data=bpy.data.lights.new(name,'AREA');data.shape='DISK';data.size=radius;data.energy=power;data.color=color
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc;look(ob,target)
light('Softbox upper left',(-.14,-.15,.43),2.35,(1,.9,.72),.28)
light('Skylight near face',(.22,-.3,.28),.95,(.74,.86,1),.22)
light('Rim',(.025,.23,.24),1.6,(1,.86,.65),.15)
bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.00055));floor=bpy.context.object
mat=bpy.data.materials.new('Warm moss studio');mat.use_nodes=True;n=mat.node_tree.nodes
base=n.get('Principled BSDF');base.inputs['Roughness'].default_value=.96
geo=n.new('ShaderNodeNewGeometry');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=12;noise.inputs['Detail'].default_value=1.1
mat.node_tree.links.new(geo.outputs['Position'],noise.inputs['Vector'])
ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.079,.115,.067,1);ramp.color_ramp.elements[1].color=(.235,.26,.14,1)
mat.node_tree.links.new(noise.outputs['Fac'],ramp.inputs[0]);mat.node_tree.links.new(ramp.outputs[0],base.inputs['Base Color'])
floor.data.materials.append(mat)
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=3
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=-.58
scene.render.resolution_x=820;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.render.filepath=str(out/'roundtrip.png')
if '--poses-only' not in sys.argv:bpy.ops.render.render(write_still=True)
if '--hero-only' in sys.argv:sys.exit(0)
camdata.ortho_scale*=1.24
scene.render.resolution_x=360;scene.render.resolution_y=275;scene.cycles.samples=10
poses={};sig=set()
for name,action in actual.items():
    rig.animation_data.action=action
    fraction={'idle':.25,'walk':.25,'takeoff':.61,'flight':.125,'touch':.5,'perch':.5}[name]
    frame=round(action.frame_range[0]+fraction*(action.frame_range[1]-action.frame_range[0]))
    scene.frame_set(frame);bpy.context.view_layer.update()
    vals=geometry();assert all(math.isfinite(v) for p in vals for v in p)
    moved=(sum(sum((a-b)**2 for a,b in zip(p,q)) for p,q in zip(points,vals))/len(vals))**.5
    poses[name]={'frame':frame,'duration_frames':round(action.frame_range[1]-action.frame_range[0])+1,'rms_vertex_offset_m':round(moved,6),'lowest_vertex_m':round(min(v[2] for v in vals),6)}
    import numpy as np
    heights=[];travel=0.; previous=None
    # Check every exported frame including attachment pivots and the complete
    # foot/wing sweep. Airborne clips can swing below the neutral rest plane.
    for f in range(round(action.frame_range[0]),round(action.frame_range[1])+1):
        scene.frame_set(f)
        deformed=[]
        for obj in meshes:
            ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());geom=ev.to_mesh()
            co=np.empty(len(geom.vertices)*3,dtype='f');geom.vertices.foreach_get('co',co)
            vv=co.reshape(-1,3);mat=np.array(ev.matrix_world)
            deformed.append(vv@mat[:3,:3].T+mat[:3,3]);ev.to_mesh_clear()
        vv=np.concatenate(deformed);assert np.isfinite(vv).all()
        heights.append(vv[:,2].min())
        if previous is not None:travel=max(travel,float(np.linalg.norm(vv-previous,axis=1).max()))
        previous=vv
        for pb in rig.pose.bones:
            if pb.parent:
                expected=pb.parent.matrix @ (pb.parent.bone.matrix_local.inverted() @ pb.bone.head_local)
                assert (pb.head-expected).length<.00001,(name,pb.name)
    poses[name].update(all_frame_min_z_m=round(float(min(heights)),6),maximum_frame_vertex_step_m=round(travel,6))
    scene.frame_set(frame)
    sig.add(tuple(round(f,6) for bone in rig.pose.bones for f in bone.matrix.to_euler()))
    assert moved>0.00002,(slug,name,moved)
    scene.render.filepath=str(out/(name+'-pose.png'));bpy.ops.render.render(write_still=True)
assert len(sig)==6
report={'source':'clean Blender 5.2 glTF import','bounds_m':[mn,mx],'six_legs':True,'distinct_sampled_poses':len(sig),'poses':poses}
(out/'roundtrip.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(report)
