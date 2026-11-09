"""Check glTF whole-page UVs, triangle interiors, masks, locked materials and skin."""
import json
import struct
from pathlib import Path
import numpy as np
from PIL import Image
from profiles import page

root=Path(__file__).resolve().parents[3]
runtime=root/'app/src/main/assets/v3'
for kind in ('ant','grasshopper'):
    data=(runtime/f'models/{kind}.glb').read_bytes()
    n=struct.unpack_from('<I',data,12)[0];g=json.loads(data[20:20+n]);binary=data[28+n:]
    def accessor(index):
        a=g['accessors'][index];bv=g['bufferViews'][a['bufferView']]
        dtype={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]
        count={'VEC2':2,'VEC3':3,'VEC4':4,'SCALAR':1}[a['type']]
        size=np.dtype(dtype).itemsize
        return np.ndarray((a['count'],count),dtype,buffer=binary,
            offset=bv.get('byteOffset',0)+a.get('byteOffset',0),
            strides=(bv.get('byteStride',size*count),size))
    m=np.array(Image.open(runtime/f'templates/{kind}-mask.png'))
    assert m.shape==(1024,1024,3) and not m[:,:,1:].any()
    triangleCount=0;painted=[];ids=m[:,:,0];regions=np.unique(ids)
    assert np.array_equal(regions,np.arange(len(regions)))
    numbers={int(i):int((ids==i).sum()) for i in regions if i}
    assert min(numbers.values())>2000
    for mesh in g['meshes']:
        for pr in mesh['primitives']:
            material=g['materials'][pr['material']]
            assert 'JOINTS_0' in pr['attributes']
            index=accessor(pr['indices']).ravel().reshape(-1,3)
            triangleCount+=len(index)
            if material['name']!='Paper_'+kind:continue
            assert mesh['name']=='PaperSurface' and material['pbrMetallicRoughness']['baseColorTexture'].get('texCoord',0)==0
            uv=accessor(pr['attributes']['TEXCOORD_0']);p=accessor(pr['attributes']['POSITION'])
            def ids_at(uvs):
                xy=(uvs*1024).astype(int)
                return ids[xy[:,1],xy[:,0]]
            assert np.all((uv>=0)&(uv<=1))
            assert ids_at(uv).min()>0
            assert set(ids_at(uv))==set(numbers)
            corners=uv[index]
            # Weight by physical surface area, including both sides of the animal.
            pos=p[index];area=np.linalg.norm(np.cross(pos[:,1]-pos[:,0],pos[:,2]-pos[:,0]),axis=1)
            surface_hits=[]
            for bary in [(1/3,1/3,1/3),(.68,.16,.16),(.16,.68,.16),(.16,.16,.68)]:
                hit=ids_at(np.einsum('tvc,v->tc',corners,bary))
                surface_hits.append(float(area[hit!=0].sum()/area.sum()))
            # An exact screen-projection subset proves head direction and UV V orientation.
            unit=.00050 if kind=='ant' else .00069;floor=224 if kind=='ant' else 232
            sx,sy=page(kind,252-p[:,0]/unit,floor-p[:,1]/unit)
            error=((uv*1024-np.stack([sx+.5,sy+.5],axis=1))**2).sum(axis=1)**.5
            direct=float((error<1).mean())
            assert direct>.20 and min(surface_hits)>.95,(kind,direct,surface_hits)
            painted.append({'mesh':mesh['name'],'skinVertices':len(uv),'triangles':len(index),
                            'directProjectedVerticesFraction':direct,'maskHitFractionsAreaWeighted':surface_hits})
    assert len(painted)==1
    stats={'byteSize':len(data),'triangles':triangleCount,'meshCount':len(g['meshes']),
           'regionsPixels':numbers,'paint':painted}
    (root/f'assets-src/expansion-114/{kind}/paint-check.json').write_text(json.dumps(stats,indent=2))
    print(kind,stats)
