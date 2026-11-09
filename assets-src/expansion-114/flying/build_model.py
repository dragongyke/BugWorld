"""Blender 5.2 background authoring. Run with -- dragonfly|honeybee."""
import bpy, sys, math, json, struct, random
from pathlib import Path
from math import sin,cos,pi
from mathutils import Vector
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pattern import *

SLUG=sys.argv[sys.argv.index('--')+1]
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'assets-src/expansion-114'/SLUG
RUNTIME=ROOT/'app/src/main/assets/v3'
DRAGON=SLUG=='dragonfly'
S=.085
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.render.fps=24
scene.render.threads_mode='FIXED';scene.render.threads=3
random.seed(835)
V=Vector
def xyz(p):return tuple(p)

def srgb(v):
    return v/12.92 if v<.04045 else ((v+.055)/1.055)**2.4
def material(name,color,rough,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF')
    lin=tuple(srgb(int(color[i:i+2],16)/255) for i in (0,2,4))
    b.inputs['Base Color'].default_value=(*lin,1);b.inputs['Roughness'].default_value=rough
    b.inputs['Metallic'].default_value=metal
    m.diffuse_color=(*lin,1)
    return m,b
paper,b=material('Paper_'+SLUG,'ffffff',.49,.07)
img=bpy.data.images.load(str(OUT/'crayon-albedo.jpg'));img.pack()
tex=paper.node_tree.nodes.new('ShaderNodeTexImage');tex.image=img
paper.node_tree.links.new(tex.outputs['Color'],b.inputs['Base Color'])
vc=paper.node_tree.nodes.new('ShaderNodeVertexColor');vc.layer_name='Membrane'
paper.node_tree.links.new(vc.outputs['Alpha'],b.inputs['Alpha'])
paper.surface_render_method='DITHERED'
eye,eyeb=material('Compound eye – '+SLUG,'3c8393' if DRAGON else '452c23',.28,.22)
facet=bpy.data.images.load(str(OUT/'compound-eye.jpg'));facet.pack()
ft=eye.node_tree.nodes.new('ShaderNodeTexImage');ft.image=facet;eye.node_tree.links.new(ft.outputs['Color'],eyeb.inputs['Base Color'])
cut,_=material('Sclerites and feet','584738' if DRAGON else '6b4432',.44,.08)
vein,_=material('Membrane venation','647f89' if DRAGON else '907550',.48,.08)
gold,_=material('Dust of pollen' if not DRAGON else 'Thoracic bronze','d79f42' if not DRAGON else 'a99762',.64)
darkfur,_=material('Chestnut pile','b07942',.8)
mats=[eye,cut,vein,gold,darkfur]

class Batch:
    def __init__(self,name,materials):
        self.name=name;self.mats=materials; self.v=[];self.uv=[];self.bones=[];self.alpha=[];self.f=[];self.mi=[]
    def add(self,p,bone,uv=(0,0),alpha=1):
        idx=len(self.v);self.v.append(tuple(float(k)*S for k in p));self.bones.append(bone)
        self.uv.append(uv);self.alpha.append(alpha);return idx
    def face(self,f,m=0):
        self.f.append(f);self.mi.append(m)
    def create(self,rig):
        me=bpy.data.meshes.new(self.name);me.from_pydata(self.v,[],self.f);me.update()
        ob=bpy.data.objects.new(self.name,me);scene.collection.objects.link(ob)
        for m in self.mats:ob.data.materials.append(m)
        uv=me.uv_layers.new(name='PaperRegistration' if self.name=='PaperSurface' else 'AnatomyUV')
        for poly,m in zip(me.polygons,self.mi):
            poly.material_index=m;poly.use_smooth=True
        for loop in me.loops:uv.data[loop.index].uv=self.uv[loop.vertex_index]
        if self.name=='PaperSurface':
            col=me.color_attributes.new(name='Membrane',type='BYTE_COLOR',domain='POINT')
            for i,a in enumerate(self.alpha):col.data[i].color=(1,1,1,a)
        for name in dict.fromkeys(self.bones):
            group=ob.vertex_groups.new(name=name);group.add([i for i,b in enumerate(self.bones) if b==name],1,'REPLACE')
        mod=ob.modifiers.new('Rigid anatomical articulation','ARMATURE');mod.object=rig;ob.parent=rig
        return ob

skin=Batch('PaperSurface',[paper]);body=Batch('Anatomy',mats)
# A projection onto a closed paper shape can hide parts of its 3D surface.
# Clamp such coordinates to the nearest surviving pixel of that anatomical part.
import numpy as np
maskImage=bpy.data.images.load(str(RUNTIME/'templates'/f'{SLUG}-mask.png'))
maskImage.colorspace_settings.name='Non-Color'
pix=np.empty(1024*1024*4,'f');maskImage.pixels.foreach_get(pix)
mask=np.rint(pix.reshape((1024,1024,4))[::-1,:,0]*255).astype('uint8')
indices=json.loads((OUT/'regions.json').read_text());keys={r['name']:r['id'] for r in indices}
trees={}
def registered(p,names):
    allowed=tuple(sorted(keys[n] for n in names if n in keys))
    x,y=sheet(SLUG,p);ix,iy=round(x),round(y)
    if not (0<=ix<1024 and 0<=iy<1024 and mask[iy,ix] in allowed):
        tree=trees.get(allowed)
        if tree is None:
            yy,xx=np.where(np.isin(mask[::2,::2],allowed));tree=KDTree(len(yy))
            for i,(qy,qx) in enumerate(zip(yy.tolist(),xx.tolist())):tree.insert((2*qx,2*qy,0),i)
            tree.balance();trees[allowed]=tree
        near=tree.find((x,y,0))[0];x,y=near.x,near.y
    return ((x+.5)/1024,1-(y+.5)/1024)
bones={'root':((0,0,.33),None)}
def hinge(name,p,parent='root'):bones[name]=(p,parent);return name

def tube(points,radii,bone,mat=1,sides=7):
    rings=[]
    for j,(p,r) in enumerate(zip(map(V,points),radii)):
        tangent=(V(points[min(j+1,len(points)-1)])-V(points[max(j-1,0)])).normalized()
        n=tangent.cross(V((0,0,1)) if abs(tangent.z)<.9 else V((0,1,0))).normalized();v=tangent.cross(n)
        rings.append([body.add(p+r*(cos(2*pi*k/sides)*n+sin(2*pi*k/sides)*v),bone) for k in range(sides)])
    for a,b0 in zip(rings,rings[1:]):
        for k in range(sides):body.face((a[k],a[(k+1)%sides],b0[(k+1)%sides],b0[k]),mat)
    body.face(tuple(reversed(rings[0])),mat);body.face(tuple(rings[-1]),mat)

def orb(center,radii,bone,paint=None,mat=0,angle=0,seg=24,nring=12):
    batch=skin if paint else body
    rings=[]; c=V(center)
    for j in range(nring+1):
        a=-pi/2+pi*j/nring;ring=[]
        for k in range(seg+1):
            phi=2*pi*k/seg
            x,y,z=cos(a)*cos(phi),cos(a)*sin(phi),sin(a)
            ox,oy,oz=x*radii[0],y*radii[1],z*radii[2]
            p=c+V((ox*cos(angle)-oz*sin(angle),oy,ox*sin(angle)+oz*cos(angle)))
            uv=paint(x,y,z) if paint else (k/seg,j/nring)
            ring.append(batch.add(p,bone,uv))
        rings.append(ring)
    for j in range(nring):
        for k in range(seg):
            a,b0=rings[j],rings[j+1]
            if j>0:batch.face((a[k],a[k+1],b0[k+1]),mat)
            if j<nring-1:batch.face((a[k],b0[k+1],b0[k]),mat)

def leg(key,coords,radii):
    name=hinge(key,coords[0]); tube(coords,radii,name,1,7)
    for no,(a,b0) in enumerate(zip(coords,coords[1:])):
        if not DRAGON and no in (0,1):
            A=V(a);B=V(b0)
            tube([a,xyz(A.lerp(B,.24)),xyz(A.lerp(B,.68)),b0],[radii[no]*.76,radii[no]*1.28,radii[no+1]*1.22,radii[no+1]],name,1,8)
    p=coords[-1]; pen=coords[-2]; side=1 if p[1]>0 else -1
    for d in [-1,1]:
        tip=(p[0]+.035,p[1]+d*.012,p[2])
        tube([p,tip],[.007,.003],name,1,5)
    return name

def build_body():
    if DRAGON:
        h=hinge('head',(.245,0,.335))
        orb((.302,0,.34),(.119,.175,.125),h,lambda x,y,z:registered((320-22*y,140-16*x),['head']))
        for s in [-1,1]:
            orb((.319,s*.133,.366),(.112,.096,.116),h,mat=0,seg=24,nring=14)
            tube([(.370,s*.042,.417),(.420,s*.065,.471),(.449,s*.092,.497),(.467,s*.124,.503)],[.014,.009,.006,.0025],h,1)
            orb((.376,s*.031,.449),(.019,.018,.019),h,mat=3,seg=12,nring=6)
        for s in [-1,1]:
            name='thorax_left' if s==-1 else 'thorax_right'
            orb((.143,s*.049,.319),(.144,.065,.12),'root',lambda x,y,z,s=s,n=name:registered(((309.7 if s==-1 else 330.3)+9*y,165.6-17.5*x),[n]))
        orb((-.077,0,.312),(.126,.077,.10),'root',lambda x,y,z:registered((320-10*y,202-14*x),['thorax_lower']))
        for k in range(7):
            bone='root' if k<3 else 'tail'
            if k==3:hinge('tail',((190-309)/165,0,.313))
            rings=[]
            for j in range(9):
                t=j/8; py=tail_dragon(k,t,.5)[1]; centerx=(190-py)/165
                radius=(tail_dragon(k,t,1)[0]-320)/165
                radius=max(.005,radius*(.84+.16*sin(pi*t)**.4))
                ring=[]
                for n in range(19):
                    a=2*pi*n/18;y=radius*cos(a);z=radius*.90*sin(a)
                    uv=registered(tail_dragon(k,t,.5-.46*cos(a)),['tail'+str(k+1)])
                    ring.append(skin.add((centerx,y,.31+.024*k/7+z),bone,uv))
                rings.append(ring)
            for aa,bb in zip(rings,rings[1:]):
                for n in range(18):skin.face((aa[n],bb[n],bb[n+1],aa[n+1]))
            skin.face(tuple(reversed(rings[-1])))
            # articulated dark sutures are continuous narrow bands
            if k<6:
                pt=(190-tail_dragon(k,1,.5)[1])/165
                tube([(pt+.009,0,.31+.024*k/7),(pt-.005,0,.31+.024*k/7)],[radius*.98,radius*.96],bone,1,18)
        for side in [-1,1]:
            for j,(x,knee,footx) in enumerate([(.17,.28,.41),(.09,.28,.13),(.01,.34,-.24)]):
                leg(f'leg{j}_{side}',[(x,side*.055,.27),(x+.01,side*.155,.20),(footx+.025,side*knee,.112),(footx,side*(knee+.005),.018),(footx+.048,side*(knee+.04),.005)],[.018,.013,.010,.006,.004])
    else:
        h=hinge('head',(.43,0,.72));hinge('tail',(-.215,0,.68))
        orb((.075,0,.737),(.465,.348,.397),'root',lambda x,y,z:registered((369+45*x,614-44*z),['thorax']),seg=32,nring=18)
        def head_registration(x,y,z):
            # The fixed compound eye cuts a hole in the paper's head. Unwrap
            # visible chitin around that hole as an annulus, following both
            # ellipses, so interpolated UVs do not run through the white center.
            theta=math.atan2(-z,x);dx,dz=cos(theta),sin(theta)
            def oval(cx,cy,rx,ry,angle):
                a=math.radians(angle)
                return (cx+rx*dx*cos(a)-ry*dz*sin(a),cy+rx*dx*sin(a)+ry*dz*cos(a))
            inner=oval(435.5,626,12.35,23.2,-7)
            outer=oval(437.3,624,26.9,39.1,8)
            frac=.13+.83*(1-y*y)
            return registered(mix(inner,outer,frac),['head'])
        orb((.618,0,.709),(.30,.267,.323),h,head_registration,seg=36,nring=20)
        for side in [-1,1]:
            orb((.68,side*.203,.721),(.151,.085,.222),h,mat=0,angle=.13,seg=28,nring=15)
            tube([(.792,side*.114,.827),(.914,side*.175,.961),(.98,side*.20,.997),(1.104,side*.264,.964),(1.20,side*.30,.901)],[.024,.018,.023,.018,.009],h,1)
            tube([(.784,side*.065,.55),(.832,side*.048,.466),(.859,side*.028,.405)],[.046,.028,.006],h,1)
        cuts=[0,.24,.44,.64,.81,.95,1]
        for k,(ta,tb) in enumerate(zip(cuts,cuts[1:])):
            rings=[]
            for j in range(6):
                t=ta+(tb-ta)*j/5
                center=V((-.17-1.22*t,0,.692-.333*t)); rad=.385*max(.008,sin(pi*(.185+.815*t))**.72)*(1-.24*t)
                ring=[]
                for q in range(25):
                    a=2*pi*q/24
                    pos=center+V((-.265*rad*sin(a),rad*.93*cos(a),rad*sin(a)))
                    board=bee_abd(t,.5-.47*sin(a))
                    ring.append(skin.add(pos,'tail',registered(board,['abdomen'+str(k+1)])))
                rings.append(ring)
            for aa,bb in zip(rings,rings[1:]):
                for q in range(24):skin.face((aa[q],bb[q],bb[q+1],aa[q+1]))
        # Individually modelled tapered setae, sparse against the eye and wing bases.
        for i in range(1600):
            x=random.uniform(-1,1); a=random.uniform(0,2*pi); d=(1-x*x)**.5
            n=V((x,d*cos(a),d*sin(a)))
            if n.z<-.78 and i%2:continue
            p=V((.075+.463*n.x,.347*n.y,.737+.394*n.z))
            end=p+V((n.x*.52-.63,n.y*.69,n.z*.57+.23)).normalized()*random.uniform(.024,.057)
            # A tiny tapered, tilted ribbon shares the baked root tones. This
            # avoids thousands of thick cylindrical spikes and extra draw calls.
            tangent=(end-p).normalized()
            v=tangent.cross(n)
            if v.length<.03:v=tangent.cross(V((0,1,0)))
            v.normalize();v*=random.uniform(.0016,.0039)
            a=body.add(p-v,'root');b=body.add(p+v,'root');c=body.add(end,'root')
            body.face((a,b,c),3 if i%3 else 4)
        for side in [-1,1]:
            for j,(x,fx,fy) in enumerate([(.32,.61,.32),(.085,-.04,.52),(-.13,-.64,.46)]):
                leg(f'leg{j}_{side}',[(x,side*.14,.577),(x+.055,side*.28,.415),(fx+.025,side*(fy-.045),.226),(fx-.025,side*fy,.035),(fx+.105,side*(fy+.047),.006)],[.043,.05 if j==2 else .034,.048 if j==2 else .027,.014,.007])

def wing_position(kind,side,t,q):
    uvp=wing(SLUG,kind,side,t,q)
    if DRAGON:
        x=(190-uvp[1])/165;y=(320-uvp[0])/165
        z=.363+.071*sin(t*pi*.86)+.019*sin(pi*q)*sin(pi*t)-.027*t*t
        return V((x,y,z))
    # A honeybee's four wings are swept backward and raised off the thorax.
    root=V((.01 if kind=='fore' else -.075,side*.224,.982 if kind=='fore' else .917))
    if kind=='fore':
        span=sin(pi*t*.5);wide=.44*(sin(pi*t)**.74)
        return root+V((-1.24*span+(.5-q)*wide*.60,side*(.73*span+(.48-q)*wide*.34),.43*span+(.5-q)*wide*1.54+.065*sin(pi*q)*sin(pi*t)))
    span=sin(pi*t*.5);wide=.34*(sin(pi*t)**.76)
    return root+V((-.99*span+(.5-q)*wide*.47,side*(.62*span+(.40-q)*wide*.29),.24*span+(.51-q)*wide*1.17+.042*sin(pi*q)*sin(pi*t)))

def wings():
    for kind in ['fore','hind']:
        for side in [-1,1]:
            root=wing_position(kind,side,0,.5)
            bone=hinge(kind+str(side),tuple(root))
            names=[f'{kind}_{side if DRAGON or kind=="fore" else -1}_cell{n}' for n in (1,2,3)]
            rows=[]
            for k in range(29):
                t=k/28;rows.append([skin.add(wing_position(kind,side,t,q/6),bone,registered(wing(SLUG,kind,side,t,q/6),names),.69 if DRAGON else .55) for q in range(7)])
            for a,bb in zip(rows,rows[1:]):
                for q in range(6):skin.face((a[q],bb[q],bb[q+1],a[q+1]))
            def ven(points,r):
                tube([xyz(wing_position(kind,side,t,q)+V((0,0,.0012))) for t,q in points],r,bone,2,5)
            for rail in [0,.27,.62,1]:
                vals=[(k/20,max(0,min(1,rail+.057*sin(pi*k/20)*sin(rail*pi)))) for k in range(21)]
                ven(vals,[.0062*(1-.72*t) if rail in (0,1) else .0048*(1-.65*t) for t,_ in vals])
            for j,t in enumerate([.20,.35,.51,.65,.77,.86,.93]):
                for n,(a,bb) in enumerate([(0,.27),(.27,.62),(.62,1)]):
                    if not DRAGON and (j+n)%3==0:continue
                    te=t+.041*(1 if n%2 else -.6)
                    q1=a+.057*sin(pi*t)*sin(a*pi);q2=bb+.057*sin(pi*te)*sin(bb*pi)
                    ven([(t,q1),((t+te)*.5,(q1+q2)*.5+.018),(te,q2)],[.0031,.0025,.002])
            if DRAGON:
                pts=[xyz(wing_position(kind,side,t,.052)+V((0,0,.003))) for t in (.69,.72,.76,.79)]
                tube(pts,[.005,.015,.016,.004],bone,1,7)
            orb(root,(.039,.035,.032),bone,mat=3,seg=12,nring=6)

build_body();wings()
arm=bpy.data.armatures.new(SLUG+' anatomical rig');rig=bpy.data.objects.new(SLUG+'_RIG',arm)
scene.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,(p,parent) in bones.items():
    bone=arm.edit_bones.new(name);bone.head=V(p)*S;bone.tail=bone.head+V((0,.06*S,0))
    if parent:bone.parent=arm.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
skin.create(rig);body.create(rig)


clips={'idle':49,'walk':25,'takeoff':25,'flight':25,'touch':33,'perch':49}
rig.animation_data_create()
for clip,length in clips.items():
    act=bpy.data.actions.new(clip);act.use_fake_user=True;rig.animation_data.action=act
    for frame in sorted(set(range(1,length+1,2))|{length}):
        t=(frame-1)/(length-1); phase=2*pi*t
        for name in bones:
            pb=rig.pose.bones[name];pb.rotation_mode='XYZ';rot=[0.,0.,0.];lift=0.
            if name=='root':
                if clip=='walk':lift=.012*sin(phase)**2
                elif clip=='takeoff':lift=.085*t*t;rot[1]=-.095*sin(pi*t)
                elif clip=='flight':lift=.034+.012*(1-cos(phase));rot[1]=.035*sin(phase)
                elif clip=='touch':lift=.057*sin(pi*t)**2;rot[1]=-.10*sin(phase)*sin(pi*t)
                elif clip=='perch':lift=.004*(1-cos(phase));rot[1]=.012*sin(phase)
                elif clip=='idle':lift=.0025*(1-cos(phase))
            elif name.startswith(('fore','hind')):
                side=int(name[-2:]) if name.endswith('-1') else 1
                hind=name.startswith('hind'); lag=.33 if hind else 0.
                if clip=='idle':angle=.018*sin(phase+lag)
                elif clip=='walk':angle=.045+.035*sin(phase*2+lag)
                elif clip=='takeoff':angle=t*((.33+.44*sin(phase*2+lag)) if DRAGON else (.20+.56*sin(phase*2+lag)))
                elif clip=='flight':angle=(.35+.43*sin(phase*2+lag)) if DRAGON else (.18+.61*sin(phase*2+lag))
                elif clip=='touch':angle=.27*sin(pi*t)**2*(1+.78*sin(phase*2+lag))
                else:angle=-.05+.030*sin(phase+lag)
                # On the dorsal sheet positive page X corresponds to negative Blender Y.
                rot[0]=(-side if DRAGON else side)*angle;rot[2]=side*(.032 if DRAGON else .074)*sin(phase)*(.4 if clip=='idle' else 1)
            elif name.startswith('leg'):
                j=int(name[3]); side=int(name.split('_')[1]); step=phase+(j+(side==1))*pi
                if clip=='walk':rot=[side*.22*max(0,sin(step)),.045*cos(step),side*.14*cos(step)]
                elif clip=='flight':rot=[side*.19,.16+.035*sin(step),-side*.11]
                elif clip=='takeoff':rot=[side*.18*t,.14*t,-side*.1*t]
                elif clip=='touch' and j==0:rot=[side*.26*sin(pi*t)**2,-.31*sin(pi*t)**2,side*.08*sin(phase)]
                elif clip=='perch':rot=[side*.045*(1-cos(phase))*(1 if j==0 else .42),.025*sin(phase+j),0]
            elif name=='head':
                rot[2]=(.16 if clip=='touch' else .036 if clip=='perch' else .020)*sin(phase)
                rot[1]=(.19 if clip=='touch' else .044 if clip=='perch' else .016)*sin(pi*t)**2
            elif name=='tail':
                rot[1]=(.09 if clip in ('flight','takeoff') else .024)*sin(phase)
            pb.rotation_euler=rot
            pb.keyframe_insert('rotation_euler',frame=frame,group=name)
            if name=='root':
                pb.location=(0,0,lift*S);pb.keyframe_insert('location',frame=frame,group=name)
        if DRAGON and clip in ('idle','walk','perch','touch','takeoff'):
            scene.frame_set(frame)
            lows=[]
            for obj in (bpy.data.objects['Anatomy'],bpy.data.objects['PaperSurface']):
                evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
                verts=evaluated.data.vertices;co=np.empty(len(verts)*3,'f')
                verts.foreach_get('co',co);lows.append(float(co[2::3].min()))
            lowest=min(lows)
            root_pose=rig.pose.bones['root']
            root_pose.location.z+=(-lowest if clip in ('walk','perch') else max(0.,-lowest))
            root_pose.keyframe_insert('location',frame=frame,group='root')
    track=rig.animation_data.nla_tracks.new();track.name=clip;track.strips.new(clip,1,act);track.mute=True
rig.animation_data.action=None
for pb in rig.pose.bones:
    pb.location=(0,0,0);pb.rotation_euler=(0,0,0)
scene.frame_set(1);bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(SLUG+'.blend')),compress=True)
dest=RUNTIME/'models'/(SLUG+'.glb')
bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',export_animations=True,export_animation_mode='ACTIONS',export_vertex_color='ACTIVE',export_yup=True,export_skins=True,export_optimize_animation_size=True)
raw=dest.read_bytes(); n=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+n])
assert {a['name'] for a in g['animations']}==set(clips)
for m in g['materials']:
    if m['name']==paper.name:
        # Vertex alpha distinguishes thin wing membrane from opaque paper body.
        m['alphaMode']='BLEND';m['doubleSided']=True
for mesh in g['meshes']:
    if mesh['name']=='PaperSurface':
        for primitive in mesh['primitives']:
            attrs=primitive['attributes']
            assert 'TEXCOORD_0' in attrs and 'COLOR_1' in attrs
            # Blender also emits a synthetic all-white set for an alpha-only
            # shader. glTF multiplies only set 0 into base color.
            attrs['COLOR_0']=attrs.pop('COLOR_1')
binary=raw[20+n:];js=json.dumps(g,separators=(',',':'),ensure_ascii=False).encode();js+=b' '*((-len(js))%4)
dest.write_bytes(struct.pack('<4sIIII',b'glTF',2,20+len(js)+len(binary),len(js),0x4e4f534a)+js+binary)
stats={'species':SLUG,'bytes':dest.stat().st_size,'triangles':sum(g['accessors'][p['indices']]['count']//3 for m in g['meshes'] for p in m['primitives']),'draw_primitives':sum(len(m['primitives']) for m in g['meshes']),'meshes':[m['name'] for m in g['meshes']],'joints':len(g['skins'][0]['joints']),'clips':list(clips),'textures':len(g['textures']),'materials':[m['name'] for m in g['materials']],'float_sheet_v0':'top','units':'metres'}
(OUT/'asset-stats.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
print(stats)
