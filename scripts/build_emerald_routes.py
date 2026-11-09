"""Sample resident ground routes against the approved forest GLB, in stage metres."""
import argparse, csv, hashlib, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', type=Path, required=True)
parser.add_argument('--flight-poses', type=Path, help='Optional CSV from verify_routes.ps1')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = args.output_dir
out.mkdir(parents=True, exist_ok=True)
source = ROOT / 'assets-src/emerald-forest-v2/garden.glb'
report = json.loads((source.parent / 'build-report.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
trees = {}
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        trees[obj.name] = BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices],
                                               [list(face.vertices) for face in obj.data.polygons])

def stage(p):
    return [p.x, p.z, -p.y]

def sample_route(name, species, coords, closed=True, trunk=False, log_side=False):
    direction = Vector((-1,0,0) if log_side else (0,1,0) if trunk else (0,0,-1))
    def hit(a, b):
        origin = Vector((8, a, b) if log_side else (a, -8, b) if trunk else (a, b, 8))
        point, normal, _, _ = trees[name].ray_cast(origin, direction, 20)
        return (point, normal) if point is not None and normal.dot(-direction) > .30 else None
    rows = []
    max_gap = 0
    min_facing = 1
    for i, (a, b) in enumerate(coords):
        contact = hit(a, b)
        assert contact, (name, species, i, a, b)
        point, normal = contact
        neighbours = [normal]
        for da, db in ((.014, 0), (-.014, 0), (0, .014), (0, -.014)):
            adjacent = hit(a + da, b + db)
            if adjacent and (adjacent[0] - point).length < .05:
                neighbours.append(adjacent[1])
        fitted = sum(neighbours, Vector()).normalized()
        if name.startswith('observe_'):
            min_facing = min(min_facing, fitted.dot((Vector((0, 0, 1.35)) - point).normalized()))
        if rows:
            for f in (.25, .5, .75):
                between = hit(last_a * (1-f) + a*f, last_b * (1-f) + b*f)
                assert between, (name, species, i, 'interpolation left surface')
                max_gap = max(max_gap, (last.lerp(point, f) - between[0]).length)
        last, last_a, last_b = point, a, b
        rows.append([round(v, 6) for v in stage(point) + stage(fitted)])
    if closed: rows[-1] = rows[0][:]
    print('SURFACE', species, name, len(rows), max_gap, min_facing, flush=True)
    assert max_gap < .003 and min_facing > 0, (species, name, max_gap, min_facing)
    return dict(species=species, surface=name, closed=closed, maxGapMetres=max_gap,
                minLeafFacingDot=min_facing if name.startswith('observe_') else None, samples=rows)

leaves = {v['name']: v['centre'] for v in report['leaves']}
def ring(species, leaf, radius, angle, aspect=1, center=None, log_side=False):
    x, y = center if center is not None else leaves[leaf][:2]
    if species == 'BUTTERFLY' and leaf == 'observe_front_right': x -= .13
    return sample_route(leaf, species, [(x + radius*math.cos(angle + math.tau*i/128),
                                          y + radius*aspect*math.sin(angle + math.tau*i/128))
                                         for i in range(129)], log_side=log_side)
routes = []
for leaf, rad, angle in [('observe_front_right', .070, math.pi), ('observe_front_low', .075, 0),
                         ('observe_back', .085, math.pi/2)]:
    routes.append(ring('BUTTERFLY', leaf, rad, angle))
for leaf, rad, angle in [('observe_front_right', .62, math.pi), ('observe_right', .63, math.pi/2),
                         ('observe_back_left', .67, -math.pi/2)]:
    routes.append(ring('LADYBUG', leaf, rad, angle, .93))
for leaf, rad, angle in [('observe_front_low', .57, 2.65), ('observe_back', .68, math.pi/2)]:
    routes.append(ring('CATERPILLAR', leaf, rad, angle, .93))

def spine(knots, steps=224):
    # x follows a piecewise Hermite trace along the longitudinal axis of each log.
    result = []
    for i in range(steps + 1):
        u = i/steps*(len(knots)-1)
        j = min(int(u), len(knots)-2)
        f = u-j
        p0, p1 = knots[j], knots[j+1]
        pprev, pnext = knots[max(0, j-1)], knots[min(len(knots)-1, j+2)]
        def pos(k):
            m0 = (p1[k] - pprev[k])/(1 if j == 0 else 2)
            m1 = (pnext[k] - p0[k])/(1 if j+1 == len(knots)-1 else 2)
            return (2*f**3-3*f**2+1)*p0[k] + (f**3-2*f**2+f)*m0 + (-2*f**3+3*f**2)*p1[k] + (f**3-f**2)*m1
        result.append((pos(0), pos(1)))
    return result
def bark_trace(name, points, trunk=False):
    # Scan around the guide through the actual bark. A ray on each interpolated
    # edge rejects holes, steep occluding ridges and jumps between branches.
    direction = Vector((0, 1, 0) if trunk else (0, 0, -1))
    def hit(x, y):
        p, n, _, _ = trees[name].ray_cast(Vector((x,-8,y) if trunk else (x,y,8)), direction, 20)
        return p if p is not None and n.dot(-direction)>.31 else None
    previous = {}
    links = []
    for i, (guide_x, y) in enumerate(points):
        candidates = {}
        orig = round(guide_x/.004)
        for col in range(orig-30, orig+31):
            x = col*.004
            point = hit(x,y)
            if point is None: continue
            cost = abs(x-guide_x)*.002
            if i == 0:
                candidates[col] = (cost,point,None)
                continue
            choices = []
            for old in (col,col-1,col+1):
                if old not in previous: continue
                total, before, _ = previous[old]
                if (point-before).length > .033: continue
                clears = True
                for f in (.25,.5,.75):
                    mid = hit((old*(1-f)+col*f)*.004,points[i-1][1]*(1-f)+y*f)
                    if mid is None or (before.lerp(point,f)-mid).length >= .0029:
                        clears = False; break
                if clears:
                    choices.append((total+cost+abs(col-old)*.003+(point-before).length*.25,old))
            if choices:
                total,old = min(choices)
                candidates[col] = (total,point,old)
        assert candidates, (name, i, guide_x, y)
        links.append({c: v[2] for c,v in candidates.items()})
        previous = candidates
    col = min(previous, key=lambda c: previous[c][0])
    result = []
    for i in reversed(range(len(points))):
        result.append((col*.004,points[i][1]))
        col = links[i][col]
    return list(reversed(result))

wood = 'CC0_foreground_fallen_log'
for guide in [[(-1.43,3.47),(-1.55,3.04),(-1.65,2.63),(-1.77,2.22),(-1.88,1.83)],
              [(-2.07,1.37),(-2.09,.96),(-2.00,.56),(-1.90,.15),(-1.97,-.22)]]:
    routes.append(sample_route(wood, 'BEETLE', bark_trace(wood, spine(guide)), False))
stump = 'CC0_hero_weathered_stump'
guide = [(-3.42,.50),(-3.42,1.08),(-3.40,1.67),(-3.42,2.25),(-3.42,2.84)]
routes.append(sample_route(stump, 'BEETLE', bark_trace(stump,spine(guide),True), False, True))
# New residents. Each perch and ground or jump support is sampled on its actual named mesh.
for species, surface, center, rx, ry, side in [
    ('DRAGONFLY','observe_front_right',(.98,3.02),.030,.026,False),
    ('DRAGONFLY','observe_back',(-.30,-1.94),.038,.032,False),
    ('HONEYBEE','detail_lotus_petal',(-.42,2.21),.026,.020,False),
    ('HONEYBEE','observe_right',(2.70,-.54),.032,.026,False),
    ('ANT','water_pad_0',(-.40,2.29),.169,.165,False),
    ('ANT','CC0_hero_weathered_stump',(3.64,1.29),.145,.21,True),
    ('GRASSHOPPER','compact_forest_bank',(0.,4.45),.26,.24,False),
    ('GRASSHOPPER','observe_back_left',(-2.60,-2.09),.255,.245,False),
]:
    route=ring(species,surface,rx,0,ry/rx,center,side)
    # Probe a point just above the visible body's origin with the full imported scene.
    row=route['samples'][0]
    point=Vector((row[0],-row[2],row[1])) + Vector((row[3],-row[5],row[4]))*.055
    for eye_height in (1.2,1.6):
        eye=Vector((0,0,eye_height))
        delta=point-eye
        blocked=[name for name,tree in trees.items() if
                 tree.ray_cast(eye,delta.normalized(),delta.length-.003)[0] is not None]
        assert not blocked, (species,surface,eye_height,blocked)
    facing=[]
    for p in route['samples']:
        toward=Vector((-p[0],1.35-p[1],-p[2])).normalized()
        facing.append(Vector(p[3:]).dot(toward))
    route['minSupportFacingDot']=min(facing)
    assert min(facing)>0, (species,surface,min(facing))
    route['spawnSightHeights']=[1.2,1.6]
    routes.append(route)

manifest = dict(sourceGlbSha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                coordinates='glTF Y-up, in metres', stride=6, routes=routes)
(out/'routes.json').write_text(json.dumps(manifest, separators=(',', ':')), encoding='utf8')
lines = ['    // BEGIN GENERATED SURFACE KNOTS',
         '    private val paths by lazy { listOf(' + ','.join(f'path{i}()' for i in range(len(routes))) + ') }']
for i, route in enumerate(routes):
    lines += [f"    // {route['species']} on {route['surface']}", f'    private fun path{i}() = SurfacePath(floatArrayOf(']
    lines += ['        ' + ','.join(f'{v:.6f}f' for v in row) + ',' for row in route['samples']]
    lines += ['    ), '+str(route['closed']).lower()+')']
lines += ['    // END GENERATED SURFACE KNOTS']
(out/'route-knots.kt').write_text('\n'.join(lines) + '\n', encoding='utf8')

if args.flight_poses:
    # Test the actual JVM flight centres against the scene, including stems and shoreline.
    previous = {}
    segments = 0
    with args.flight_poses.open() as stream:
        for row in csv.DictReader(stream):
            key = row['species'], row['index']
            point = Vector((float(row['x']), -float(row['z']), float(row['y'])))
            old = previous.get(key)
            airborne = row['airborne'] == 'true'
            previous[key] = point, airborne
            if old is None or not (old[1] or airborne): continue
            before = old[0]
            segment = point - before
            if segment.length < .00001: continue
            segments += 1
            for name, tree in trees.items():
                crossing = tree.ray_cast(before, segment.normalized(), segment.length)[0]
                assert crossing is None, (key, row['time'], name, crossing)
    assert segments > 0
    print('Verified', segments, 'airborne centre segments against', len(trees), 'forest meshes')
