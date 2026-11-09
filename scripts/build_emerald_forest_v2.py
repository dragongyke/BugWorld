"""Asset continuation: dimensional shore, photographic forest, portable water.

The deliverable GLB contains the garden and sparse middle distance. Background
crowns use a CC0 panorama with a matching HDR source. No app asset is modified.
"""
import json
import math
import random
import shutil
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_emerald_forest_review as review
import assets_v3_garden as g

ROOT = review.ROOT
OUT = review.out
assert OUT == ROOT / 'assets-src/emerald-forest-v2'
SOURCE = ROOT / 'assets-src/emerald-forest-review/garden.glb'
TEX = OUT / 'textures'
TEX.mkdir(parents=True, exist_ok=True)
shutil.copy2(SOURCE.parent/'forest-ground-albedo.png',OUT/'forest-ground-albedo.png')
random.seed(1122)
review.SKY_RADIUS=12
review.SKY_CENTRE=(0,0,1.6)
review.IBL_STRENGTH=.7
review.SUN_ENERGY=3.2
review.EXPOSURE=.15
review.BEETLE_XY=(-1.55,2.65)
review.ASSET_SOURCE=SOURCE
review.FERN_CLUSTERS=40
review.IBL_SOURCE=OUT/'sources/forest_slope_4k.exr'
review.WATER_NOTE='Static thin alpha-blended PBR over a shallow bed, metallic 0; no physical refraction. Native animated shader is a separate editor probe.'
review.LEAVES=[
    ('observe_front_right',(1.75,2.65,.55),.93,(-.21,-.20,1),True),
    ('observe_front_low',(1.30,1.15,.12),.91,(-.09,-.12,1),True),
    ('observe_right',(2.70,-.50,.30),1.0,(-.22,.07,1),False),
    ('observe_back',(.30,-2.90,.30),1.30,(-.02,.24,1),False),
    ('observe_back_left',(-2.60,-2.10,.30),1.25,(.24,.14,1),False),
]
review.ANCHOR_XY={'ladybug':(1.70,2.55),'caterpillar':(1.30,1.15)}


def device():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for dev in prefs.devices:
        dev.use = dev.type == 'OPTIX'
    scene.cycles.device = 'GPU'
    scene.cycles.use_denoising = True
    scene.cycles.seed = 1122
    scene.view_settings.view_transform = 'AgX'


def principled(mat):
    return next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')


def image_node(mat, path, noncolor=False):
    node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = bpy.data.images.load(str(path), check_existing=True)
    if noncolor:
        node.image.colorspace_settings.name = 'Non-Color'
    node.image.pack()
    return node


def bake_material_image(mat, socket, name, size=1024, normal=False):
    """Bake authored nodes into a portable texture, without painting source images."""
    scene = bpy.context.scene
    ns, ls = mat.node_tree.nodes, mat.node_tree.links
    output = next(n for n in ns if n.type == 'OUTPUT_MATERIAL')
    old = output.inputs['Surface'].links[0].from_socket
    if not normal:
        emit = ns.new('ShaderNodeEmission')
        ls.new(socket, emit.inputs['Color'])
        ls.new(emit.outputs[0], output.inputs['Surface'])
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0,0,50))
    plane = bpy.context.object
    plane.data.materials.append(mat)
    im = bpy.data.images.new(name, width=size, height=size)
    if normal:
        im.colorspace_settings.name = 'Non-Color'
    dst = ns.new('ShaderNodeTexImage')
    dst.image = im
    ns.active = dst
    scene.cycles.samples = 4
    bpy.ops.object.bake(type='NORMAL' if normal else 'EMIT', margin=8,
                       normal_space='TANGENT')
    im.filepath_raw = str(TEX / (name+'.png'))
    im.file_format = 'PNG'
    im.save()
    im.pack()
    bpy.data.objects.remove(plane, do_unlink=True)
    if not normal:
        ls.new(old, output.inputs['Surface'])
        ns.remove(emit)
    return dst




def make_water():
    """Thin blended shallow-water study; no transmission dependency in the GLB.

    The floor-like pigment is baked. Moving normals are a separate native shader
    deliverable, not claimed by this static glTF material.
    """
    mat = g.material('pond_clear_shallows', (.09,.25,.16), .12)
    ns, ls = mat.node_tree.nodes, mat.node_tree.links
    bs = principled(mat)
    bs.inputs['Metallic'].default_value = 0
    bs.inputs['IOR'].default_value = 1.333
    uv = ns.new('ShaderNodeTexCoord')
    noise = ns.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 22
    noise.inputs['Detail'].default_value = 3
    noise.inputs['Roughness'].default_value = .7
    ls.new(uv.outputs['UV'], noise.inputs['Vector'])
    ramp = ns.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = .23
    ramp.color_ramp.elements[0].color = (.025,.105,.069,1)
    ramp.color_ramp.elements[1].position = .80
    ramp.color_ramp.elements[1].color = (.24,.43,.23,1)
    ls.new(noise.outputs['Fac'], ramp.inputs[0])
    pigment = bake_material_image(mat, ramp.outputs['Color'], 'shallow_water_pigment', 512)
    bs.inputs['Base Color'].default_value=(.018,.080,.060,1)
    # Normal baking with alpha < 1 yields a uniform (128,128,128) image in
    # Blender 5.2. Bake the opaque surface first and validate the actual pixels.
    bs.inputs['Alpha'].default_value=1
    bs.inputs['Specular IOR Level'].default_value=1
    # Fine irregular ripples rather than the old broad metallic swirls.
    noise.inputs['Scale'].default_value = 34
    noise.inputs['Detail'].default_value = 2
    noise.inputs['Roughness'].default_value = .45
    mapping = ns.new('ShaderNodeVectorMath')
    mapping.operation = 'MULTIPLY'
    mapping.inputs[1].default_value = (1,2.8,1)
    ls.new(uv.outputs['UV'],mapping.inputs[0])
    ls.new(mapping.outputs[0],noise.inputs['Vector'])
    bump=ns.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value=.4
    bump.inputs['Distance'].default_value=.015
    ls.new(noise.outputs['Fac'],bump.inputs['Height'])
    ls.new(bump.outputs[0],bs.inputs['Normal'])
    normal = bake_material_image(mat, bump.outputs[0], 'water_fine_ripple_normal', 1024, True)
    pixels=list(normal.image.pixels)
    assert max(pixels[2::4])>.95 and max(pixels[0::4])-min(pixels[0::4])>.02, 'Invalid flat normal bake'
    bs.inputs['Alpha'].default_value=.72
    bs.inputs['Roughness'].default_value=.065
    mat.surface_render_method='DITHERED'
    nm=ns.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value=1.0
    ls.new(normal.outputs['Color'],nm.inputs['Color'])
    ls.new(nm.outputs[0],bs.inputs['Normal'])
    # Keep the water under the irregular bank. The old square extended beyond
    # the bank and created a false turquoise horizon through the forest.
    bpy.data.objects.remove(bpy.data.objects['pond_water'],do_unlink=True)
    def pond_disk(name, height, material):
        vertices=[(0,0,height)]
        for i in range(160):
            a=i*math.tau/160
            r=review.bank_radius(a)+.45
            vertices.append((r*math.cos(a),r*math.sin(a),height))
        faces=[(0,i+1,(i+1)%160+1) for i in range(160)]
        uv=[(v[0]/12+.5,v[1]/12+.5) for v in vertices]
        return g.addmesh(name,vertices,faces,material,uv)
    pond_disk('pond_water',-.10,'pond_clear_shallows')
    # One low bed and a few coarse pebbles provide real depth beneath the thin
    # blended surface; there is no Cycles-only refraction dependency.
    bed=g.material('shallow_pond_bed',(.15,.25,.13),.85)
    bt=bed.node_tree.nodes.new('ShaderNodeTexImage');bt.image=pigment.image
    bed.node_tree.links.new(bt.outputs['Color'],principled(bed).inputs['Base Color'])
    pond_disk('pond_bed',-.35,'shallow_pond_bed')
    for index in range(45):
        a=index*2.399963;r=.5+(index%11)*.32
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,
            location=(r*math.cos(a),r*math.sin(a),-.36))
        rock=bpy.context.object
        rock.scale=(random.uniform(.11,.23),random.uniform(.08,.19),random.uniform(.04,.10))
        rock.data.materials.append(bed)
        for poly in rock.data.polygons:poly.use_smooth=True
    bed_rocks=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('Icosphere')]
    # Name selected newly-created pebbles explicitly before joining.
    bpy.ops.object.select_all(action='DESELECT')
    for ob in bed_rocks:ob.select_set(True)
    if bed_rocks:
        bpy.context.view_layer.objects.active=bed_rocks[0];bpy.ops.object.join()
        bed_rocks[0].name='submerged_pebbles'


def make_petals():
    mat=g.MATS['lotus_petal']
    ns,ls=mat.node_tree.nodes,mat.node_tree.links
    bs=principled(mat)
    uv=ns.new('ShaderNodeTexCoord')
    sep=ns.new('ShaderNodeSeparateXYZ')
    ls.new(uv.outputs['UV'],sep.inputs[0])
    ramp=ns.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position=.02
    ramp.color_ramp.elements[0].color=(.86,.63,.38,1)
    e=ramp.color_ramp.elements.new(.35); e.color=(1,.91,.83,1)
    ramp.color_ramp.elements[1].position=1
    ramp.color_ramp.elements[1].color=(.93,.40,.57,1)
    ls.new(sep.outputs['Y'],ramp.inputs[0])
    tex=bake_material_image(mat,ramp.outputs['Color'],'lotus_petal_daylight',512)
    ls.new(tex.outputs['Color'],bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value=.46
    # Old normal map was based on saturated artwork and made petals appear crumpled.
    for link in list(bs.inputs['Normal'].links):
        ls.remove(link)
    for link in list(bs.inputs['Emission Color'].links):
        ls.remove(link)
    bs.inputs['Emission Strength'].default_value=0


def make_leaves():
    mat=g.MATS['lotus_leaf']; ns,ls=mat.node_tree.nodes,mat.node_tree.links
    bs=principled(mat)
    old=bs.inputs['Base Color'].links[0].from_socket
    mix=ns.new('ShaderNodeMixRGB')
    mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
    mix.inputs[2].default_value=(1.20,1.38,.48,1)
    ls.new(old,mix.inputs[1])
    tex=bake_material_image(mat,mix.outputs[0],'lotus_emerald_pigment',1254)
    ls.new(tex.outputs['Color'],bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value=.42
    for link in list(bs.inputs['Roughness'].links):
        ls.remove(link)
    bs.inputs['Roughness'].default_value=.30
    bs.inputs['Specular IOR Level'].default_value=.5
    for node in ns:
        if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.22


def import_source(name):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(OUT/'sources'/name/(name+'_1k.gltf')))
    meshes=sorted([ob for ob in set(bpy.data.objects)-before if ob.type=='MESH'],key=lambda ob:ob.name)
    return meshes


def cutout(mat,name,alpha):
    bs=principled(mat)
    tex=image_node(mat,OUT/'sources'/name/'textures'/alpha,True)
    mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Alpha'])
    mat.surface_render_method='DITHERED'
    mat.use_backface_culling=False


def instance(template, name, position, scale, rotation=0):
    ob=bpy.data.objects.new(name,template.data)
    bpy.context.collection.objects.link(ob)
    ob.location=position
    ob.scale=(scale,scale,scale)
    ob.rotation_euler.z=rotation
    return ob


def shore_rocks():
    templates=import_source('rock_moss_set_01')
    for ob in templates:
        # The scan's local origin is at its supporting surface.
        review.simplify(ob,min(1,1100/len(ob.data.polygons)))
    rocks=[]
    # Irregular overlapping groups, embedded in the shore, rather than a necklace.
    for i in range(12):
        a=(i//2)*math.tau/6+(i%2)*.17+random.uniform(-.06,.06)
        r=review.bank_radius(a)+random.uniform(.35,.7)
        ob=instance(templates[i%6],f'shore_rock_{i}',
                    (r*math.cos(a),r*math.sin(a),-.10),random.uniform(.50,.72),a)
        rocks.append(ob)
    for ob in templates:bpy.data.objects.remove(ob,do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in rocks: ob.select_set(True)
    bpy.context.view_layer.objects.active=rocks[0]
    bpy.ops.object.join()
    rocks[0].name='bank_moss_stones'


def near_ferns():
    templates=import_source('fern_02')
    cutout(bpy.data.materials['fern_02'],'fern_02','fern_02_alpha_1k.png')
    # Only distant shore vegetation uses reduced maps. Keep interactive leaf and
    # wood textures unchanged in resolution. Source downloads remain untouched.
    for node in bpy.data.materials['fern_02'].node_tree.nodes:
        if node.type=='TEX_IMAGE' and node.image and max(node.image.size)>512:
            node.image.scale(512,512)
            node.image.pack()
    template=next(ob for ob in templates if ob.name=='fern_02_a')
    ferns=[]
    for i in range(40):
        a=i*2.399963+.12
        r=review.bank_radius(a)+random.uniform(.6,1.6 if i<22 else 2.9)
        z=bank_height(r,a)
        ferns.append(instance(template,'shore_fern',(r*math.cos(a),r*math.sin(a),z),
                              random.uniform(2.3,3.2),a))
    for ob in templates:bpy.data.objects.remove(ob,do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in ferns:ob.select_set(True)
    bpy.context.view_layer.objects.active=ferns[0]
    bpy.ops.object.join()
    ferns[0].name='shore_ferns'


def rounded_flowers():
    for name in ('detail_lotus_petal','detail_gold'):
        bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    # Rounded, cupped petals; fewer overlapping layers expose the golden heart.
    for centre,scale in [((-.38,2.05,.35),1),((2.9,2.3,.24),.88),((-1.25,-3,.31),.75)]:
        for layer,(count,length,width,rise) in enumerate([(10,.44,.16,.12),(8,.32,.13,.19),(6,.21,.09,.21)]):
            for k in range(count):
                a=k*math.tau/count+layer*.36
                vs,fs,uv=[],[],[]
                for j in range(13):
                    t=j/12
                    w=width*math.sin(math.pi*t)**.55
                    for q in range(7):
                        s=q/3-1
                        x=w*s*scale;y=length*t*scale
                        z=(rise*t**1.8+.045*s*s*math.sin(math.pi*t))*scale
                        vs.append((centre[0]+x*math.cos(a)+y*math.sin(a),
                                   centre[1]-x*math.sin(a)+y*math.cos(a),centre[2]+z))
                        uv.append((q/6,t))
                for j in range(12):
                    for q in range(6):
                        n=j*7+q;fs.append((n,n+1,n+8,n+7))
                g.batch('lotus_petal',vs,fs,uv)
        for k in range(32):
            a=k*2.399;r=.065*math.sqrt(k/32)*scale
            b=Vector(centre)+Vector((r*math.cos(a),r*math.sin(a),.035*scale))
            tip=b+Vector((r*.7*math.cos(a),r*.7*math.sin(a),.10*scale))
            g.tube('stamen',[tuple(b),tuple(tip)],[.002*scale,.005*scale],'gold',4,True)
    for mat,(vs,fs,uv) in g.BATCH.items():
        g.addmesh('detail_'+mat,vs,fs,mat,uv)
    g.BATCH.clear()


def flush(prefix):
    result=[]
    for mat,(vs,fs,uv) in g.BATCH.items():
        if vs: result.append(g.addmesh(prefix+mat,vs,fs,mat,uv))
    g.BATCH.clear()
    return result






def foliage_materials():
    bark=g.material('forest_bark',(.2,.14,.065),.85)
    bs=principled(bark)
    source=ROOT/'assets-src/v3-review/garden/sources/dead_tree_trunk_02/textures'
    tex=image_node(bark,source/'dead_tree_trunk_02_diff_2k.jpg')
    bark.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    tex=image_node(bark,source/'dead_tree_trunk_02_nor_gl_2k.jpg',True)
    n=bark.node_tree.nodes.new('ShaderNodeNormalMap')
    n.inputs['Strength'].default_value=.5
    bark.node_tree.links.new(tex.outputs['Color'],n.inputs['Color'])
    bark.node_tree.links.new(n.outputs[0],bs.inputs['Normal'])
    for i,color in enumerate([(.19,.35,.035),(.29,.44,.055),(.10,.25,.024)]):
        m=g.material('canopy_'+str(i),color,.62)
        m.use_backface_culling=False




def bank_height(radius, angle):
    t=max(0,min(1,(radius-review.bank_radius(angle))/3.5))
    # A high circular ridge exposed a broad lawn and cut across the forest floor.
    # Keep the shore low; the sparse roots/ferns provide the middle-distance edge.
    edge=max(0,(t-.63)/.37)
    return -.14+.38*t+.12*math.sin(angle*5)*t+.06*math.cos(angle*9)*t-1.05*edge*edge


def forest_floor_material():
    """Replace speckled study pigment with a registered 1K forest scan."""
    mat=g.MATS['forest_bank'];bs=principled(mat)
    source=OUT/'sources/forest_leaves_02'
    tex=image_node(mat,source/'forest_leaves_02_diffuse_1k.jpg')
    mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    normal=image_node(mat,source/'forest_leaves_02_nor_gl_1k.jpg',True)
    n=mat.node_tree.nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.35
    mat.node_tree.links.new(normal.outputs['Color'],n.inputs['Color'])
    mat.node_tree.links.new(n.outputs[0],bs.inputs['Normal'])


def observation_layout():
    # Preserve sizes; move the two front surfaces to open the centre. The log
    # occupies the left viewing sector, so remove its obstructed redundant leaf.
    for ob in list(bpy.context.scene.objects):
        if ob.name.startswith('observe_') or ob.name in ('detail_leaf_vein','detail_dew','compact_forest_bank'):
            bpy.data.objects.remove(ob,do_unlink=True)
    for i,(name,centre,radius,normal,detail) in enumerate(review.LEAVES):
        g.leaf(name,centre,radius,normal,i,detail)
    flush('detail_')
    review.simplify(bpy.data.objects['detail_leaf_vein'],.35)
    vertices,faces,uv=[],[],[]
    for ring in range(5):
        for i in range(160):
            a=i*math.tau/160
            r=review.bank_radius(a)+3.5*ring/4
            vertices.append((r*math.cos(a),r*math.sin(a),bank_height(r,a)))
            uv.append((vertices[-1][0]/2,vertices[-1][1]/2))
    for ring in range(4):
        for i in range(160):
            a=ring*160+i;b=ring*160+(i+1)%160
            faces.append((a,a+160,b+160,b))
    g.addmesh('compact_forest_bank',vertices,faces,'forest_bank',uv)


def build_near():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    device()
    for mat in bpy.data.materials:g.MATS[mat.name]=mat
    for name in ['bank_moss_stones','detail_fern_0','detail_fern_1','detail_fern_2','detail_stem']:
        bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    # Budget reclaimed from tiny vein cylinders, not the observed leaf silhouette.
    observation_layout()
    review.simplify(bpy.data.objects['CC0_hero_weathered_stump'],.75)
    review.simplify(bpy.data.objects['CC0_foreground_fallen_log'],.75)
    review.simplify(bpy.data.objects['CC0_moss_on_branches'],.8)
    make_water()
    make_petals()
    rounded_flowers()
    make_leaves()
    foliage_materials()
    forest_floor_material()
    shore_rocks()
    # Taller relief and shrubs break the previously exposed flat ring.
    bank=bpy.data.objects['compact_forest_bank']
    for v in bank.data.vertices:
        p=v.co
        a=math.atan2(p.y,p.x)
        p.z=bank_height(math.hypot(p.x,p.y),a)
    near_ferns()
    # The photographic canopy already supplies distant trunks. Bare helper
    # trunks exposed cut tips when looking up, even when extended past the sky;
    # keep the middle-distance depth in the real rocks, ferns and approved wood.
    flush('shore_')
    bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.context.scene.objects: ob.select_set(ob.type=='MESH')
    bpy.ops.export_scene.gltf(filepath=str(OUT/'garden.glb'),export_format='GLB',
        use_selection=True,export_yup=True,export_animations=False,export_cameras=False,export_lights=False)
    review.patch_mask(OUT/'garden.glb')
    raw=(OUT/'garden.glb').read_bytes();length=struct.unpack_from('<I',raw,12)[0]
    doc=json.loads(raw[20:20+length])
    for mat in doc['materials']:
        if mat['name']=='fern_02':
            mat['alphaMode']='MASK';mat['alphaCutoff']=.45
    encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*(-len(encoded)%4)
    tail=raw[20+length:]
    (OUT/'garden.glb').write_bytes(struct.pack('<4sII',b'glTF',2,20+len(encoded)+len(tail))+
        struct.pack('<I4s',len(encoded),b'JSON')+encoded+tail)




def prepare_photographic_background():
    # Downsample a genuine 8K CC0 panorama to the explicit mobile texture budget.
    # No enlargement, synthetic extra detail, or claim that this is an HDR image.
    im=bpy.data.images.load(str(OUT/'sources/forest_slope.jpg'),check_existing=False)
    source_size=list(im.size)
    im.scale(4096,2048)
    im.filepath_raw=str(OUT/'forest-panorama.png')
    im.file_format='PNG';im.save()
    (OUT/'panorama-source.json').write_text(json.dumps({
        'kind':'CC0 photographic forest, reduced for mobile texture budget',
        'source':'https://polyhaven.com/a/forest_slope','author':'Andreas Mischok',
        'sourceResolution':source_size,'resolution':[4096,2048],
        'runtimeMiddleTrunks':0,'runtimeFarTrees':0,
        'note':'Tonemapped colour panorama. Matching 4K unclipped EXR retained separately for IBL.'
    },indent=2))


if not review.args.render_only:
    build_near()
prepare_photographic_background()
review.actual_render()
