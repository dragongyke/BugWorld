"""Asset-only emerald forest study. Export, reimport, then render actual geometry.

Never writes runtime assets. Cycles reflection/lighting is preview evidence only.
"""
import argparse
import collections
import hashlib
import json
import math
import random
import struct
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import assets_v3_garden as garden
from build_stage_candidate import patch_mask

p = argparse.ArgumentParser()
p.add_argument('--output-dir', type=Path, required=True)
p.add_argument('--render-only', action='store_true')
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = args.output_dir.resolve()
assert out in (ROOT / 'assets-src/emerald-forest-review', ROOT / 'assets-src/emerald-forest-v2')
out.mkdir(parents=True, exist_ok=True)
PANORAMA = out / 'forest-panorama.png'
GROUND = out / 'forest-ground-albedo.png'
SOURCE = ROOT / 'assets-src/stage111-geometry/garden.glb'
random.seed(112)

# Blender uses Z-up; export converts to glTF Y-up. Origin is entry centre.
LEAVES = [
    ('observe_front_right', (1.40, 2.15, .55), .93, (-.21, -.20, 1), True),
    ('observe_front_low', (.65, 1.40, .12), .91, (-.09, -.12, 1), True),
    ('observe_right', (2.70, -.50, .30), 1.0, (-.22, .07, 1), False),
    ('observe_back', (.30, -2.90, .30), 1.30, (-.02, .24, 1), False),
    ('observe_back_left', (-2.60, -2.10, .30), 1.25, (.24, .14, 1), False),
    ('observe_left', (-3.90, .40, .20), 1.40, (.18, -.16, 1), False),
]


def bank_radius(angle):
    """Keep solid bank/rocks outside the observation leaves' full projected discs."""
    direction = Vector((math.cos(angle), math.sin(angle)))
    radius = 4.0 + .35 * math.sin(angle * 3) + .17 * math.sin(angle * 7)
    for _, (x, y, _), leaf_radius, _, _ in LEAVES:
        centre = Vector((x, y))
        projection = centre.dot(direction)
        perpendicular2 = centre.length_squared - projection * projection
        margin = leaf_radius + .4
        if perpendicular2 < margin * margin:
            radius = max(radius, projection + math.sqrt(margin * margin - perpendicular2))
    return radius


def mesh_bounds(ob):
    points = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return (Vector(tuple(min(v[i] for v in points) for i in range(3))),
            Vector(tuple(max(v[i] for v in points) for i in range(3))))


def simplify(ob, ratio):
    bpy.context.view_layer.objects.active = ob
    mod = ob.modifiers.new('Review budget reduction', 'DECIMATE')
    mod.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=mod.name)


def export_unlit_background(path):
    """Emission in Blender alone exports lit emissive PBR; require explicit glTF unlit."""
    raw = path.read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20+size])
    assert len(doc['materials']) == 1
    mat = doc['materials'][0]
    texture = mat.pop('emissiveTexture')
    color = mat.pop('emissiveFactor')
    mat['pbrMetallicRoughness'] = dict(baseColorFactor=[*color, 1],
                                     baseColorTexture=texture, metallicFactor=0, roughnessFactor=1)
    mat.setdefault('extensions', {})['KHR_materials_unlit'] = {}
    doc['extensionsUsed'] = sorted(set(doc.get('extensionsUsed', []) + ['KHR_materials_unlit']))
    doc['extensionsRequired'] = sorted(set(doc.get('extensionsRequired', []) + ['KHR_materials_unlit']))
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    tail = raw[20+size:]
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, 20+len(encoded)+len(tail)) +
                     struct.pack('<I4s', len(encoded), b'JSON') + encoded + tail)


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    for mat in bpy.data.materials:
        garden.MATS[mat.name] = mat
    log = bpy.data.objects['CC0_foreground_fallen_log']
    stump = bpy.data.objects['CC0_hero_weathered_stump']
    trees = {
        ob.name: BVHTree.FromPolygons(
            [ob.matrix_world @ v.co for v in ob.data.vertices],
            [list(f.vertices) for f in ob.data.polygons])
        for ob in (log, stump)
    }
    # Rigid move preserves the approved wood silhouette/scale and its moss.
    lo, hi = mesh_bounds(log)
    centre = (lo + hi) / 2
    coordinates = np.array([tuple(log.matrix_world @ v.co)[:2] for v in log.data.vertices])
    _, vectors = np.linalg.eigh(np.cov(coordinates.T))
    axis = vectors[:, -1]
    angle = math.atan2(1, .2) - math.atan2(axis[1], axis[0])
    log_xform = (Matrix.Translation(Vector((-1.75, 1.70, centre.z - .12))) @
                 Matrix.Rotation(angle, 4, 'Z') @ Matrix.Translation(-centre))
    lo, hi = mesh_bounds(stump)
    stump_xform = Matrix.Translation(Vector((-3.45, 3.65, -.16)) -
                                    Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)))
    transforms = {log.name: log_xform, stump.name: stump_xform}
    moss = bpy.data.objects['CC0_moss_on_branches']
    verts = [moss.matrix_world @ v.co for v in moss.data.vertices]
    parent = list(range(len(verts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for e in moss.data.edges:
        a, b = e.vertices
        parent[find(a)] = find(b)
    groups = collections.defaultdict(list)
    for i in range(len(verts)):
        groups[find(i)].append(i)
    for ids in groups.values():
        c = sum((verts[i] for i in ids), Vector()) / len(ids)
        owner = min(trees, key=lambda name: trees[name].find_nearest(c)[3])
        for i in ids:
            moss.data.vertices[i].co = transforms[owner] @ verts[i]
    moss.matrix_world = Matrix.Identity(4)
    for ob in (log, stump):
        ob.matrix_world = transforms[ob.name] @ ob.matrix_world
    # New routes will be sampled on this derivative, not reused from the old wood.
    simplify(log, .55)
    keep = {log.name, stump.name, moss.name, 'pond_water'}
    for ob in list(bpy.context.scene.objects):
        if ob.name not in keep:
            bpy.data.objects.remove(ob, do_unlink=True)

    # Daylight leaf pigment uses the project's original leaf painting; no baked lights.
    mat = garden.MATS['lotus_leaf']
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    base = bsdf.inputs['Base Color'].links[0].from_node
    assert base.type == 'TEX_IMAGE'
    base.image = bpy.data.images.load(str(ROOT / 'assets-src/v3-review/garden/sources/project-original-textures/leaf.png'))
    base.image.pack()
    for link in list(bsdf.inputs['Roughness'].links):
        mat.node_tree.links.remove(link)
    bsdf.inputs['Roughness'].default_value = .63
    bsdf.inputs['Specular IOR Level'].default_value = .24
    bsdf.inputs['Metallic'].default_value = 0
    mat.use_backface_culling = False
    for i, (name, centre, radius, normal, detail) in enumerate(LEAVES):
        garden.leaf(name, centre, radius, normal, i, detail)
    for i, (x, y, r) in enumerate([(-.4, 2.3, .35), (1.55, 3.1, .35),
                                   (-.5, -3.15, .35), (-2.8, -.1, .35)]):
        garden.leaf(f'water_pad_{i}', (x, y, -.045), r, (0, 0, 1), i, False)
    # Flower islands leave a quiet open central view and separate flight waypoints.
    for pos, scale, bud in [((-.38, 2.05, .35), 1, False),
                            ((2.9, 2.3, .24), .88, False),
                            ((-1.25, -3.0, .31), .75, True)]:
        garden.flower(pos, scale, bud)
    petal_mat = garden.MATS['lotus_petal']
    petal_bsdf = next(n for n in petal_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    for link in list(petal_bsdf.inputs['Base Color'].links):
        petal_mat.node_tree.links.remove(link)
    petal_bsdf.inputs['Base Color'].default_value = (1, .52, .66, 1)
    petal_bsdf.inputs['Roughness'].default_value = .62
    if 'Emission Strength' in petal_bsdf.inputs:
        petal_bsdf.inputs['Emission Strength'].default_value = 0

    # Reeds stay below eye level and occur only at a few banks.
    for x, y in [(-3.1, -.3), (3.5, 1.8), (2.8, -2.6), (-1.6, -3.5)]:
        for k in range(6):
            garden.reed(x + random.uniform(-.2, .2), y + random.uniform(-.2, .2),
                        random.uniform(.35, .7), random.random() * math.tau, k % 3)
    # Low fronds: real silhouette geometry, opaque, joined by material.
    for shade in range(3):
        garden.material(f'fern_{shade}', [(.13, .27, .045), (.19, .34, .07),
                                         (.24, .40, .095)][shade], .78)
    for cluster in range(28):
        a = cluster * math.tau / 28 + random.uniform(-.08, .08)
        radius = bank_radius(a) + random.uniform(.25, .60)
        c = Vector((radius * math.cos(a), radius * math.sin(a), .12))
        for frond in range(4):
            angle = a + frond * 1.61
            direction = Vector((math.cos(angle), math.sin(angle), 0))
            side = Vector((-direction.y, direction.x, 0))
            length = random.uniform(.42, .75)
            points = [c + direction * (length * j / 12) + Vector((0, 0, .55 * math.sin(j / 12 * 2.3)))
                      for j in range(13)]
            garden.tube('fern_rachis', [tuple(v) for v in points], .003, 'stem', 3, True)
            for j in range(1, 12):
                t = j / 12
                w = .13 * math.sin(math.pi * t)**.7
                for sign in (-1, 1):
                    b = points[j]
                    tip = b + side * w * sign + direction * .055 + Vector((0, 0, .015))
                    centre = (tip + b) / 2
                    width = direction * .017
                    garden.batch(f'fern_{cluster % 3}', [tuple(b), tuple(centre - width),
                                  tuple(tip), tuple(centre + width)], [(0, 1, 2, 3)])
    for material, (verts, faces, uv) in garden.BATCH.items():
        ob = garden.addmesh('detail_' + material, verts, faces, material, uv)
        if material == 'lotus_petal':
            simplify(ob, .35)

    # A low shore defines a finite clearing instead of endless water.
    ground_mat = garden.material('forest_bank', (1, 1, 1), .91)
    ns, ls = ground_mat.node_tree.nodes, ground_mat.node_tree.links
    tex = ns.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(GROUND)); tex.image.pack()
    ls.new(tex.outputs['Color'], ns['Principled BSDF'].inputs['Base Color'])
    vs, fs, uv = [], [], []
    sectors, rings = 160, 5
    for ring in range(rings):
        t = ring / (rings - 1)
        for i in range(sectors):
            a = i * math.tau / sectors
            r = bank_radius(a) + 3.5 * t
            z = -.13 + .30 * math.sin(t * math.pi / 2) + .08 * math.sin(a * 6) * t
            vs.append((r * math.cos(a), r * math.sin(a), z))
            uv.append((vs[-1][0] / 2, vs[-1][1] / 2))
    for j in range(rings - 1):
        for i in range(sectors):
            a, b = j * sectors + i, j * sectors + (i + 1) % sectors
            fs.append((a, a + sectors, b + sectors, b))
    garden.addmesh('compact_forest_bank', vs, fs, 'forest_bank', uv)
    rocks = []
    for index in range(24):
        a = index * math.tau / 24 + random.uniform(-.12, .12)
        r = bank_radius(a) + .35
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1,
                                             location=(r*math.cos(a), r*math.sin(a), .10))
        rock = bpy.context.object; rock.name = f'bank_moss_stone_{index}'
        rock.scale = (random.uniform(.35, .7), random.uniform(.3, .55), random.uniform(.22, .5))
        for v in rock.data.vertices:
            v.co *= 1 + .12 * math.sin(v.co.x * 7 + v.co.y * 3) * math.cos(v.co.z * 6)
        rock.data.materials.append(ground_mat)
        layer = rock.data.uv_layers.new(name='UVMap')
        for poly in rock.data.polygons:
            poly.use_smooth = True
            for loop in poly.loop_indices:
                co = rock.data.vertices[rock.data.loops[loop].vertex_index].co
                layer.data[loop].uv = (co.x*.35 + co.z*.2, co.y*.35 + co.z*.2)
        rocks.append(rock)
    bpy.ops.object.select_all(action='DESELECT')
    for rock in rocks:
        rock.select_set(True)
    bpy.context.view_layer.objects.active = rocks[0]; bpy.ops.object.join()
    rocks[0].name = 'bank_moss_stones'
    water = bpy.data.objects['pond_water']
    water_mat = water.data.materials[0]
    # Low-poly water geometry; portable static PBR sample. Animated shader is a later device probe.
    mesh = bpy.data.meshes.new('single_pond_surface')
    mesh.from_pydata([(-9, -9, -.10), (9, -9, -.10), (9, 9, -.10), (-9, 9, -.10)],
                     [], [(0, 1, 2, 3)])
    mesh.materials.append(water_mat)
    uv = mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:
        v = mesh.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (v.x * .24, v.y * .24)
    water.data = mesh
    bsdf = next(n for n in water_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (.10, .21, .16, 1)
    bsdf.inputs['Roughness'].default_value = .11
    bsdf.inputs['Metallic'].default_value = .38
    bsdf.inputs['IOR'].default_value = 1.333
    bsdf.inputs['Transmission Weight'].default_value = 0
    normal = next(n for n in water_mat.node_tree.nodes if n.type == 'NORMAL_MAP')
    normal.inputs['Strength'].default_value = 1.25
    for ob in bpy.context.scene.objects:
        ob.select_set(ob.type == 'MESH')
    bpy.ops.export_scene.gltf(filepath=str(out / 'garden.glb'), export_format='GLB',
                             use_selection=True, export_yup=True, export_animations=False,
                             export_cameras=False, export_lights=False)
    patch_mask(out / 'garden.glb')


def actual_render():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(out / 'garden.glb'))
    scene = bpy.context.scene
    assets = [o for o in scene.objects if o.type == 'MESH']
    # Triangle-level intersection checks target the reported wood/leaf regression.
    contact_objects = [bpy.data.objects[name] for name, *_ in LEAVES]
    wood_objects = [bpy.data.objects[name] for name in
                    ('CC0_foreground_fallen_log', 'CC0_hero_weathered_stump',
                     'compact_forest_bank', 'bank_moss_stones')]
    trees = {ob.name: BVHTree.FromPolygons([ob.matrix_world @ v.co for v in ob.data.vertices],
                                          [list(f.vertices) for f in ob.data.polygons])
             for ob in contact_objects + wood_objects}
    collisions = []
    pairs = [(a, b) for a in contact_objects for b in wood_objects]
    pairs += [(a, b) for i, a in enumerate(contact_objects) for b in contact_objects[i+1:]]
    for a, b in pairs:
        overlaps = trees[a.name].overlap(trees[b.name])
        if overlaps:
            collisions.append(dict(a=a.name,b=b.name,trianglePairs=len(overlaps)))
    (out/'contact-check.json').write_text(json.dumps(dict(pairsChecked=len(pairs),intersections=collisions),indent=2))
    assert not collisions, collisions
    # Verify leaves from standing and seated centre; coarse clearance is not collision proof.
    checks = []
    for name, centre, radius, normal, _ in LEAVES:
        n = Vector(normal).normalized()
        checks.append(dict(name=name,centre=list(centre),radius=radius,
                           frontDotStanding=round(n.dot((Vector((0, 0, 1.65)) - Vector(centre)).normalized()), 4),
                           frontDotSeated=round(n.dot((Vector((0, 0, 1.15)) - Vector(centre)).normalized()), 4)))
    # Actual mesh contact anchors for species layout, sampled after export.
    anchor_requests = [('beetle', 'CC0_foreground_fallen_log', globals().get('BEETLE_XY', (-1.65, 1.65)), .48),
                       ('ladybug', 'observe_front_right', (1.35, 2.05), .31),
                       ('caterpillar', 'observe_front_low', (.65, 1.4), .40),
                       ('butterfly', 'detail_lotus_petal', (-.30, 2.25), .48)]
    anchors = []
    for kind, surface, xy, span in anchor_requests:
        xy=globals().get('ANCHOR_XY',{}).get(kind,xy)
        ob = bpy.data.objects[surface]
        tree = BVHTree.FromPolygons([ob.matrix_world @ v.co for v in ob.data.vertices],
                                    [list(f.vertices) for f in ob.data.polygons])
        pos, normal, _, _ = tree.ray_cast(Vector((*xy, 8)), Vector((0, 0, -1)), 20)
        if kind == 'beetle':
            # Choose the upper surface of the real wood close to the requested spot.
            hits = []
            for dx in np.linspace(-.8, .8, 17):
                for dy in np.linspace(-.8, .8, 17):
                    hit, n, _, _ = tree.ray_cast(Vector((xy[0]+dx, xy[1]+dy, 8)),
                                                Vector((0, 0, -1)), 20)
                    if hit is not None and n.z > .75:
                        hits.append(((hit-Vector((*xy, .8))).length + 3*(1-n.z), hit, n))
            _, pos, normal = min(hits, key=lambda item:item[0])
        assert pos is not None and normal.z > .2, (kind, surface)
        anchors.append(dict(species=kind,surface=surface,point=list(pos),normal=list(normal),span=span))

    scene.world = bpy.data.worlds.new('Forest panorama IBL preview')
    scene.world.use_nodes = True
    ns, ls = scene.world.node_tree.nodes, scene.world.node_tree.links
    env = ns.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(str(globals().get('IBL_SOURCE',PANORAMA))); env.image.pack()
    ls.new(env.outputs['Color'], ns['Background'].inputs['Color'])
    ns['Background'].inputs['Strength'].default_value = globals().get('IBL_STRENGTH', 1.10)
    # Finite background places its shoreline below eye height. A world at infinity
    # incorrectly raises the pond's bank to the viewer's eye plane.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32,
        radius=globals().get('SKY_RADIUS', 9), location=globals().get('SKY_CENTRE', (0,0,0)))
    sky = bpy.context.object; sky.name = 'REVIEW_forest_sky'
    sky.visible_shadow = False
    sky_mat = bpy.data.materials.new('forest_background_unlit'); sky_mat.use_nodes = True
    sn, sl = sky_mat.node_tree.nodes, sky_mat.node_tree.links
    sn.clear()
    st = sn.new('ShaderNodeTexImage'); st.image = bpy.data.images.load(str(PANORAMA)); st.image.pack()
    emit = sn.new('ShaderNodeEmission'); emit.inputs['Strength'].default_value = .8
    output = sn.new('ShaderNodeOutputMaterial')
    sl.new(st.outputs['Color'], emit.inputs['Color']); sl.new(emit.outputs[0], output.inputs['Surface'])
    sky.data.materials.append(sky_mat)
    bpy.ops.object.select_all(action='DESELECT'); sky.select_set(True)
    background_temp=out/'forest-background-export.glb'
    bpy.ops.export_scene.gltf(filepath=str(background_temp),export_format='GLB',
                             use_selection=True,export_yup=True,export_animations=False,
                             export_cameras=False,export_lights=False)
    export_unlit_background(background_temp)
    background_final=out/'forest-background.glb'
    # Editors may retain an open handle to the unchanged sky source on Windows.
    # Do not overwrite identical bytes or accept a partial export as complete.
    if not background_final.exists() or background_temp.read_bytes()!=background_final.read_bytes():
        background_temp.replace(background_final)
    else:
        background_temp.unlink()
    bpy.data.objects.remove(sky, do_unlink=True)
    before_sky = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(out/'forest-background.glb'))
    for ob in set(bpy.data.objects) - before_sky:
        if ob.type == 'MESH':
            ob.visible_shadow = False
    bpy.ops.object.light_add(type='SUN', location=(-3, -2, 6))
    sun = bpy.context.object; sun.name = 'PREVIEW_warm_sun'
    sun.rotation_euler = (Vector((0, 2, .5)) - sun.location).to_track_quat('-Z', 'Y').to_euler()
    sun.data.energy = globals().get('SUN_ENERGY',3.0)
    sun.data.angle = math.radians(3); sun.data.color = (1, .94, .82)

    # Approved real rigs are review markers, separate from the environment GLB.
    insect_sources = []
    insect_object_names = []
    for anchor in anchors:
        before = set(bpy.data.objects)
        source = ROOT / 'assets-src/stage111-geometry' / (anchor['species'] + '.glb')
        bpy.ops.import_scene.gltf(filepath=str(source))
        added = [o for o in bpy.data.objects if o not in before]
        insect_object_names.extend(o.name for o in added)
        meshes = [o for o in added if o.type == 'MESH' and not o.hide_render and o.visible_get()]
        rig = next(o for o in added if o.type == 'ARMATURE')
        rig.animation_data.action = None
        for track in rig.animation_data.nla_tracks:
            track.mute = 'idle' not in track.name
        scene.frame_set(5); bpy.context.view_layer.update()
        pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
        low = Vector(tuple(min(v[i] for v in pts) for i in range(3)))
        high = Vector(tuple(max(v[i] for v in pts) for i in range(3)))
        span = max(high.x - low.x, high.y - low.y)
        factor = anchor['span'] / span
        centre = Vector(((high.x + low.x) / 2, (high.y + low.y) / 2, low.z))
        q = Vector((0, 0, 1)).rotation_difference(Vector(anchor['normal']))
        transform = (Matrix.Translation(Vector(anchor['point']) + Vector(anchor['normal']) * .004)
                     @ q.to_matrix().to_4x4() @ Matrix.Scale(factor, 4) @ Matrix.Translation(-centre))
        for ob in added:
            if ob.parent not in added:
                ob.matrix_world = transform @ ob.matrix_world
        insect_sources.append(dict(species=anchor['species'],sha256=hashlib.sha256(source.read_bytes()).hexdigest()))

    bpy.ops.object.camera_add(location=(0, 0, 1.6))
    camera = bpy.context.object; camera.name = 'Review_entry_camera'; scene.camera = camera
    camera.data.lens = 18; camera.data.clip_start = .03; camera.data.clip_end = 100
    scene.render.engine = 'CYCLES'; scene.cycles.samples = 40; scene.cycles.seed = 112
    scene.cycles.use_denoising = True
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    assert any(d.type == 'OPTIX' for d in prefs.devices)
    for d in prefs.devices:
        d.use = d.type == 'OPTIX'
    scene.cycles.device = 'GPU'
    scene.render.resolution_x = 1440; scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = globals().get('EXPOSURE',0)
    views = [('front', (0, 2.4, 1.25)), ('right', (2.4, 0, 1.25)),
             ('back', (0, -2.4, 1.25)), ('left', (-2.4, 0, 1.25))]
    for name, target in views:
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(out / (name + '.png'))
        bpy.ops.render.render(write_still=True)
    camera.rotation_euler = (Vector(views[0][1]) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    # The editable environment must not duplicate four already-versioned rig packages.
    # Review renders above include them; rerunning the script restores their references.
    for name in insect_object_names:
        ob = bpy.data.objects.get(name)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'emerald-forest-review.blend'), compress=True)
    report = dict(
        status='Asset design study; not installed and not headset evidence',
        skySphereRadiusMetres=globals().get('SKY_RADIUS',9),
        skyCentre=list(globals().get('SKY_CENTRE',(0,0,0))),
        skyPreviewShadowVisibility=False,
        waterMaterialNote=globals().get('WATER_NOTE','Art-directed static PBR metallic 0.38; not physical water. Needs device shader probe.'),
        sourceSha256=hashlib.sha256(globals().get('ASSET_SOURCE',SOURCE).read_bytes()).hexdigest(),
        glbSha256=hashlib.sha256((out / 'garden.glb').read_bytes()).hexdigest(),
        gardenTriangles=sum(sum(len(f.vertices)-2 for f in o.data.polygons) for o in assets),
        gardenMeshes=len(assets), gardenMaterials=len({m.name for o in assets for m in o.data.materials}),
        waterTriangles=sum(len(f.vertices)-2 for f in bpy.data.objects['pond_water'].data.polygons),
        heroLeaves=len(LEAVES),waterPads=4,flowers=3,reeds=24,fernClusters=globals().get('FERN_CLUSTERS',28),
        leaves=checks,anchors=anchors,reviewInsects=insect_sources,leafWoodIntersections=collisions,
        limitations=['Cycles world/reflection/tonemapping are not PICO runtime evidence',
                     'garden GLB is static; any native water probe is separate and not integrated',
                     'anchors are design samples, not completed collision-safe loop routes',
                     'leaf-facing dot checks do not prove no occlusion or no intersections',
                     'panorama seam and poles must be verified in the actual sky sphere'])
    (out / 'build-report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    assert PANORAMA.is_file() and GROUND.is_file()
    if not args.render_only:
        build()
    actual_render()
