"""Check the actual shipped glTF UVs against every red-channel region on the sheet."""
from pathlib import Path
import json,struct
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3]; V3=ROOT/'app/src/main/assets/v3'
def check(slug):
    raw=(V3/'models'/(slug+'.glb')).read_bytes();length=struct.unpack_from('<I',raw,12)[0]
    g=json.loads(raw[20:20+length]); binary=raw[28+length:]
    def values(i):
        a=g['accessors'][i]; b=g['bufferViews'][a['bufferView']]
        dtype={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]
        width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
        return np.frombuffer(binary,dtype=dtype,offset=b.get('byteOffset',0)+a.get('byteOffset',0),count=a['count']*width).reshape(-1,width)
    mesh=next(m for m in g['meshes'] if m['name']=='PaperSurface')
    assert len(mesh['primitives'])==1
    p=mesh['primitives'][0];material=g['materials'][p['material']]
    assert material['name']=='Paper_'+slug and material['alphaMode']=='BLEND'
    uv=values(p['attributes']['TEXCOORD_0']); faces=values(p['indices']).reshape(-1,3)
    alpha=np.unique(values(p['attributes']['COLOR_0'])[:,3])
    assert len(alpha)==2 and alpha[0]/alpha[-1]<.8
    registered=np.asarray(Image.open(V3/'templates'/(slug+'-mask.png')))[:,:,0]
    centers=uv[faces].mean(axis=1)*1024
    hits=registered[centers[:,1].astype(int),centers[:,0].astype(int)]
    coverage=Image.new('1',(1024,1024)); draw=ImageDraw.Draw(coverage)
    for tri in (uv[faces]*1024).tolist():draw.polygon([tuple(pt) for pt in tri],fill=1)
    occupied=np.asarray(coverage)
    report={'region_coverage':{},'face_centroids_outside_percent':round(float(np.mean(hits==0))*100,2),'wing_opacity':round(float(alpha[0]/alpha[-1]),3)}
    for i in range(1,registered.max()+1):
        region=registered==i
        report['region_coverage'][int(i)]=round(float(occupied[region].mean()),3)
        assert report['region_coverage'][i]>.12,(slug,i,report)
    (ROOT/'assets-src/expansion-114'/slug/'uv-check.json').write_text(json.dumps(report,indent=2))
    print(slug,report)
if __name__=='__main__':
    for slug in ['dragonfly','honeybee']:check(slug)
