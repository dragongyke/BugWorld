"""Lossless GLB batching: only static sibling mesh nodes sharing one skin/material.

No decimation/rebake. Protected paint nodes, bones, clips, textures and all vertex
bytes are retained. Unsupported geometry fails closed. Original review exports
are inputs; derivatives and a provenance/verification report go to a new folder.
"""
import argparse
import copy
import hashlib
import json
import struct
from collections import defaultdict
from pathlib import Path

import numpy as np
from audit_stage_glb import read_glb, audit

ROOT=Path(__file__).resolve().parents[1]
PROTECTED={
    'butterfly': {'L_forewing_closed_membrane','R_forewing_closed_membrane',
                  'L_hindwing_closed_membrane','R_hindwing_closed_membrane'},
    'beetle': {'elytron_L','elytron_R','pronotum_and_short_horn','head_and_recurved_horn'},
    'ladybug': {'elytron_L','elytron_R','head','pronotum'},
    'caterpillar': {'ONE continuous wrinkled soft cuticle'},
}
DTYPES={5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}
WIDTHS={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}


def values(doc,binary,index):
    a=doc['accessors'][index]
    assert 'sparse' not in a and 'extensions' not in a
    v=doc['bufferViews'][a['bufferView']]
    dtype=np.dtype(DTYPES[a['componentType']])
    width=WIDTHS[a['type']]
    offset=v.get('byteOffset',0)+a.get('byteOffset',0)
    stride=v.get('byteStride',width*dtype.itemsize)
    return np.ndarray((a['count'],width),dtype,buffer=binary,offset=offset,
                      strides=(stride,dtype.itemsize)).copy()


def merge(kind,out):
    source=ROOT/f'assets-src/v3-review/{kind}/{kind}.glb'
    raw,original,binary=read_glb(source)
    doc=copy.deepcopy(original)
    data=bytearray(binary)
    parents={c:i for i,n in enumerate(doc['nodes']) for c in n.get('children',[])}
    animated={c['target'].get('node') for a in doc.get('animations',[]) for c in a['channels']}
    joints={i for skin in doc.get('skins',[]) for i in skin['joints']}
    groups=defaultdict(list)
    for i,n in enumerate(doc['nodes']):
        if 'mesh' not in n or n.get('name') in PROTECTED[kind]:
            continue
        # Identity local transform, common parent and identical skin imply the same
        # coordinate system in both bind pose and every animation frame.
        assert set(n)<= {'mesh','name','skin'} and i in parents and 'skin' in n
        assert i not in animated and i not in joints
        mesh=doc['meshes'][n['mesh']]
        assert set(mesh)<= {'name','primitives'} and len(mesh['primitives'])==1
        p=mesh['primitives'][0]
        assert set(p)<= {'attributes','indices','material','mode'} and p.get('mode',4)==4
        formats=tuple((key,doc['accessors'][a]['componentType'],doc['accessors'][a]['type'],
                       doc['accessors'][a].get('normalized',False)) for key,a in sorted(p['attributes'].items()))
        groups[(parents[i],n['skin'],p.get('material'),formats)].append(i)

    def accessor(array,template,target):
        while len(data)%4: data.append(0)
        content=array.tobytes()
        view=len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer':0,'byteOffset':len(data),'byteLength':len(content),'target':target})
        data.extend(content)
        item={k:copy.deepcopy(v) for k,v in template.items() if k in ('componentType','type','normalized')}
        item.update(bufferView=view,count=len(array))
        if 'min' in template: item['min']=array.min(axis=0).tolist()
        if 'max' in template: item['max']=array.max(axis=0).tolist()
        index=len(doc['accessors']);doc['accessors'].append(item)
        return index

    removed=set()
    checks=[]
    for group,nodes in groups.items():
        if len(nodes)<2: continue
        primitives=[doc['meshes'][doc['nodes'][i]['mesh']]['primitives'][0] for i in nodes]
        merged={'attributes':{},'mode':4,'material':primitives[0]['material']}
        sizes=[doc['accessors'][p['attributes']['POSITION']]['count'] for p in primitives]
        for attribute in primitives[0]['attributes']:
            arrays=[values(original,binary,p['attributes'][attribute]) for p in primitives]
            joined=np.concatenate(arrays)
            merged['attributes'][attribute]=accessor(joined,doc['accessors'][primitives[0]['attributes'][attribute]],34962)
            # Byte-for-byte comparison after packing, before source accessors are removed.
            readback=values(doc,data,merged['attributes'][attribute])
            start=0
            for array in arrays:
                assert readback[start:start+len(array)].tobytes()==array.tobytes()
                start+=len(array)
        indices=[];offset=0
        for p,count in zip(primitives,sizes):
            original_indices=values(original,binary,p['indices']).astype('<u4')
            assert original_indices.max()<count
            indices.append(original_indices+offset);offset+=count
        index_type=5123 if offset<=65536 else 5125
        joined_indices=np.concatenate(indices).astype(DTYPES[index_type])
        merged['indices']=accessor(joined_indices,{'componentType':index_type,'type':'SCALAR'},34963)
        # Draw order and every original triangle remain intact within this material.
        cursor=0;offset=0
        readback=values(doc,data,merged['indices']).astype('<u4')
        for p,count in zip(primitives,sizes):
            old=values(original,binary,p['indices']).astype('<u4')
            assert np.array_equal(readback[cursor:cursor+len(old)]-offset,old)
            cursor+=len(old);offset+=count
        survivor=doc['nodes'][nodes[0]]
        mesh_index=len(doc['meshes'])
        doc['meshes'].append({'name':'batch_'+survivor['name'],'primitives':[merged]})
        survivor['mesh']=mesh_index
        checks.append({'material':doc['materials'][group[2]]['name'],
                       'sourceNodes':[original['nodes'][i]['name'] for i in nodes],
                       'vertices':offset,'triangles':len(joined_indices)//3,
                       'vertexBytesAndTriangleIndicesIdentical':True})
        removed.update(nodes[1:])

    # Compact node references, including animation and skin references.
    remap={i:new for new,i in enumerate(i for i in range(len(doc['nodes'])) if i not in removed)}
    for scene in doc['scenes']: scene['nodes']=[remap[i] for i in scene['nodes']]
    for n in doc['nodes']:
        if 'children' in n: n['children']=[remap[i] for i in n['children'] if i not in removed]
    for skin in doc['skins']:
        skin['joints']=[remap[i] for i in skin['joints']]
        if 'skeleton' in skin: skin['skeleton']=remap[skin['skeleton']]
    for animation in doc['animations']:
        for channel in animation['channels']:
            channel['target']['node']=remap[channel['target']['node']]
    doc['nodes']=[n for i,n in enumerate(doc['nodes']) if i not in removed]
    used_meshes=sorted({n['mesh'] for n in doc['nodes'] if 'mesh' in n})
    meshes={old:new for new,old in enumerate(used_meshes)}
    for n in doc['nodes']:
        if 'mesh' in n: n['mesh']=meshes[n['mesh']]
    doc['meshes']=[doc['meshes'][i] for i in used_meshes]

    used=set()
    for mesh in doc['meshes']:
        for p in mesh['primitives']: used.update(p['attributes'].values());used.add(p['indices'])
    for skin in doc['skins']: used.add(skin['inverseBindMatrices'])
    for a in doc['animations']:
        for sampler in a['samplers']: used.update((sampler['input'],sampler['output']))
    ids={old:new for new,old in enumerate(sorted(used))}
    accessor_hashes={new:hashlib.sha256(values(doc,data,old).tobytes()).hexdigest() for old,new in ids.items()}
    for mesh in doc['meshes']:
        for p in mesh['primitives']:
            p['attributes']={k:ids[v] for k,v in p['attributes'].items()};p['indices']=ids[p['indices']]
    for skin in doc['skins']: skin['inverseBindMatrices']=ids[skin['inverseBindMatrices']]
    for a in doc['animations']:
        for sampler in a['samplers']:
            for key in ('input','output'):sampler[key]=ids[sampler[key]]
    doc['accessors']=[doc['accessors'][i] for i in sorted(used)]
    used_views={a['bufferView'] for a in doc['accessors']}|{i['bufferView'] for i in doc['images']}
    views={old:new for new,old in enumerate(sorted(used_views))}
    packed=bytearray();new_views=[]
    for i in sorted(used_views):
        v=copy.deepcopy(doc['bufferViews'][i])
        while len(packed)%4:packed.append(0)
        content=data[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
        v['byteOffset']=len(packed);packed.extend(content);new_views.append(v)
    for a in doc['accessors']:a['bufferView']=views[a['bufferView']]
    for i in doc['images']:i['bufferView']=views[i['bufferView']]
    doc['bufferViews']=new_views;doc['buffers']=[{'byteLength':len(packed)}]
    text=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode()
    text+=b' '*((-len(text))%4);packed+=b'\0'*((-len(packed))%4)
    output=out/(kind+'.glb')
    output.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(text)+len(packed))+
                       struct.pack('<I4s',len(text),b'JSON')+text+
                       struct.pack('<I4s',len(packed),b'BIN\0')+packed)

    # Validate serialized output, not only the in-memory construction.
    _,after,after_binary=read_glb(output)
    for index,expected in accessor_hashes.items():
        assert hashlib.sha256(values(after,after_binary,index).tobytes()).hexdigest()==expected
    assert original['materials']==after['materials'] and original['textures']==after['textures']
    for before_image,after_image in zip(original['images'],after['images']):
        bv=original['bufferViews'][before_image['bufferView']];av=after['bufferViews'][after_image['bufferView']]
        assert binary[bv.get('byteOffset',0):bv.get('byteOffset',0)+bv['byteLength']]==after_binary[av['byteOffset']:av['byteOffset']+av['byteLength']]
    for a,b in zip(original['animations'],after['animations']):
        assert a['name']==b['name'] and len(a['channels'])==len(b['channels'])
        for ca,cb in zip(a['channels'],b['channels']):
            assert ca['target']['path']==cb['target']['path']
            assert original['nodes'][ca['target']['node']]['name']==after['nodes'][cb['target']['node']]['name']
        for sa,sb in zip(a['samplers'],b['samplers']):
            assert sa.get('interpolation')==sb.get('interpolation')
            for key in ('input','output'):
                assert values(original,binary,sa[key]).tobytes()==values(after,after_binary,sb[key]).tobytes()
    for a,b in zip(original['skins'],after['skins']):
        assert [original['nodes'][i]['name'] for i in a['joints']]==[after['nodes'][i]['name'] for i in b['joints']]
        assert values(original,binary,a['inverseBindMatrices']).tobytes()==values(after,after_binary,b['inverseBindMatrices']).tobytes()
    assert PROTECTED[kind]<={n.get('name') for n in after['nodes']}
    before=audit(source);after_stats=audit(output)
    assert before['triangles']==after_stats['triangles'] and before['vertices']==after_stats['vertices']
    return {'species':kind,'source':str(source.relative_to(ROOT)),'sourceSha256':hashlib.sha256(raw).hexdigest(),
            'outputSha256':after_stats['sha256'],
            'before':{k:before[k] for k in ('nodes','primitives','triangles','vertices','bytes')},
            'after':{k:after_stats[k] for k in ('nodes','primitives','triangles','vertices','bytes')},
            'animations':[a['name'] for a in after['animations']],'verifiedBatches':checks,
            'texturesMaterialsSkinAndAnimationBytesRetained':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=ROOT/'assets-src/insects-batched')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    report={'method':'lossless sibling batching; no vertex/UV/skin/material/image/animation simplification',
            'assets':[merge(kind,args.out) for kind in PROTECTED],
            'limits':'Static identity checks only; fresh Blender import and headset performance remain separate.'}
    (args.out/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([{k:r[k] for k in ('species','before','after')} for r in report['assets']]))
