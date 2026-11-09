import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

root = Path(__file__).resolve().parents[1]
bindings = {
    'butterfly': {'Continuous wax pigment • image PBR': ['L_forewing_closed_membrane', 'R_forewing_closed_membrane', 'L_hindwing_closed_membrane', 'R_hindwing_closed_membrane']},
    'caterpillar': {'Continuous wax pigment • image PBR': ['ONE continuous wrinkled soft cuticle']},
    'beetle': {'left_green_elytron': ['elytron_L'], 'right_green_elytron': ['elytron_R'], 'lavender_pronotum': ['pronotum_and_short_horn'], 'warm_ivory_wax': ['head_and_recurved_horn']},
    'ladybug': {'left_pink_wax': ['elytron_L'], 'right_mint_wax': ['elytron_R'], 'warm_brown_cuticle': ['head'], 'ivory_collar_with_brown_smudge': ['pronotum']},
}
report = {}
for species, materials in bindings.items():
    raw = (root / f'assets-src/v3-review/{species}/{species}.glb').read_bytes()
    json_length = struct.unpack_from('<I', raw, 12)[0]
    data = json.loads(raw[20:20+json_length])
    binary = raw[28+json_length:]
    def accessor(index):
        a = data['accessors'][index]
        view = data['bufferViews'][a['bufferView']]
        assert a['componentType'] == 5126
        count = {'VEC2': 2, 'VEC3': 3}[a['type']]
        offset = view.get('byteOffset', 0) + a.get('byteOffset', 0)
        return np.ndarray((a['count'], count), dtype='<f4', buffer=binary, offset=offset,
                          strides=(view.get('byteStride', count*4), 4))
    nodes = {n['name']: n for n in data['nodes'] if 'mesh' in n}
    geometry = {}
    for name, targets in materials.items():
        for target in targets:
            primitive = data['meshes'][nodes[target]['mesh']]['primitives'][0]
            assert data['materials'][primitive['material']]['name'] == name, (species, target, name)
            geometry[target] = accessor(primitive['attributes']['POSITION']), accessor(primitive['attributes']['TEXCOORD_0'])
    facts = {}
    if species == 'butterfly':
        for side, uv in [('L', (.49, .49)), ('R', (.51, .49))]:
            p, t = geometry[f'{side}_forewing_closed_membrane']
            distance = np.linalg.norm(t-np.array(uv), axis=1).min()
            assert distance < .00001, (side, distance)
            facts[f'{side}_forewing_root_uv'] = list(uv)
    elif species == 'caterpillar':
        p, t = geometry['ONE continuous wrinkled soft cuticle']
        dorsal = np.argmin(np.linalg.norm(t-np.array((.5,.25)), axis=1))
        ventral = np.argmin(np.linalg.norm(t-np.array((.5,.75)), axis=1))
        assert p[dorsal,1] > p[ventral,1]+.04
        facts['dorsal_uv'] = t[dorsal].tolist()
        facts['ventral_uv'] = t[ventral].tolist()
    else:
        p, t = geometry['elytron_L']
        top = np.argmin(np.linalg.norm(t-np.array((.5,1)), axis=1))
        edge = np.argmin(np.linalg.norm(t-np.array((.5,0)), axis=1))
        assert p[top,1] > p[edge,1]+.035
        facts['shell_seam_uv'] = t[top].tolist()
        facts['shell_outer_edge_uv'] = t[edge].tolist()
    mask = np.array(Image.open(root/f'app/src/main/assets/v3/templates/{species}-mask.png'))
    locked = Image.open(root/f'assets-src/v3-review/lineart/masks/{species}-locked-2048.png').resize((1024,1024),Image.Resampling.NEAREST)
    assert mask.shape == (1024,1024,3) and not mask[:,:,1:].any()
    assert not mask[:,:,0][np.array(locked)>0].any(), species
    report[species] = {'material_node_bindings': materials, 'exported_glb_landmarks': facts, 'protected_mask_verified': True}
(root/'docs/V3-Paint-Verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: four GLB material/node bindings, exported UV orientation landmarks, and four protected runtime masks')

# The new species store the full paper projection in the skinned surface's UVs.
from PIL import ImageDraw
from audit_stage_glb import read_glb

extra = {}
for slug in ('dragonfly', 'honeybee', 'ant', 'grasshopper'):
    runtime = root/'app/src/main/assets/v3'
    raw, glb, binary = read_glb(runtime/'models'/f'{slug}.glb')
    node = next(n for n in glb['nodes'] if n.get('name') == 'PaperSurface' and 'mesh' in n)
    assert 'skin' in node, slug
    mask = np.array(Image.open(runtime/'templates'/f'{slug}-mask.png').convert('RGB'))
    assert mask.shape == (1024,1024,3) and not mask[:,:,1:].any(), slug
    ids = mask[:,:,0]
    assert np.array_equal(np.unique(ids),np.arange(ids.max()+1)), slug
    coverage = Image.new('L',(1024,1024))
    draw = ImageDraw.Draw(coverage)
    def values(index,dtype,columns):
        a = glb['accessors'][index]
        view = glb['bufferViews'][a['bufferView']]
        width = np.dtype(dtype).itemsize
        return np.ndarray((a['count'],columns),dtype=dtype,buffer=binary,
                          offset=view.get('byteOffset',0)+a.get('byteOffset',0),
                          strides=(view.get('byteStride',width*columns),width))
    for p in glb['meshes'][node['mesh']]['primitives']:
        mat = glb['materials'][p['material']]
        assert mat['name']==f'Paper_{slug}' and 'baseColorTexture' in mat['pbrMetallicRoughness'],slug
        assert 'JOINTS_0' in p['attributes'] and 'WEIGHTS_0' in p['attributes'],slug
        uv = values(p['attributes']['TEXCOORD_0'],'<f4',2)
        assert np.isfinite(uv).all() and uv.min()>=-.001 and uv.max()<=1.001,(slug,uv.min(),uv.max())
        typ = {5121:'u1',5123:'<u2',5125:'<u4'}[glb['accessors'][p['indices']]['componentType']]
        tris = values(p['indices'],typ,1).reshape(-1,3)
        points = np.floor(uv*1024).astype(int).tolist()
        for a,b,c in tris:
            draw.polygon([tuple(points[a]),tuple(points[b]),tuple(points[c])],fill=255)
    covered = np.array(coverage)>0
    fractions = {int(i):round(float(np.mean(covered[ids==i])),3) for i in np.unique(ids) if i}
    assert min(fractions.values())>.60,(slug,'poorly covered color region',fractions)
    extra[slug] = {'regions':len(fractions),'fractionOfEachRegionReachedByUV':fractions}
dest = root/'.work/expansion-paint.json'
dest.parent.mkdir(exist_ok=True)
dest.write_text(json.dumps(extra,indent=2)+'\n',encoding='utf-8')
print('PASS: four new skinned paper surfaces, every coloring region reachable through exported UVs')
