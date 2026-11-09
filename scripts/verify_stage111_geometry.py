"""Verify candidate provenance and unchanged bindings, plus every triangle's index range."""
import hashlib,json,struct
from pathlib import Path
from audit_stage_glb import read_glb
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'assets-src/stage111-geometry'
manifest=json.loads((folder/'manifest.json').read_text())
surfaces={r['surface'] for r in json.loads((ROOT/'assets-src/stage-ring/garden-routes.json').read_text())['routes']}
surfaces.add('pond_water')
reports=[]
for entry in manifest['results']:
    source,base,old_bin=read_glb(ROOT/entry['source'])
    target,doc,new_bin=read_glb(folder/f"{entry['kind']}.glb")
    assert hashlib.sha256(source).hexdigest()==entry['sourceSha256']
    assert hashlib.sha256(target).hexdigest()==entry['sha256']
    assert new_bin[:len(old_bin)]==old_bin
    for key in ('nodes','skins','animations','materials','textures','images','samplers'):
        assert base.get(key)==doc.get(key),(entry['kind'],key)
    assert doc['accessors'][:len(base['accessors'])]==base['accessors']
    assert doc['bufferViews'][:len(base['bufferViews'])]==base['bufferViews']
    protected={n['mesh'] for n in base['nodes'] if n.get('name') in surfaces}
    triangles=0
    for mi,(before,after) in enumerate(zip(base['meshes'],doc['meshes'],strict=True)):
        assert before['name']==after['name']
        for a,b in zip(before['primitives'],after['primitives'],strict=True):
            assert {k:v for k,v in a.items() if k!='indices'}=={k:v for k,v in b.items() if k!='indices'}
            if entry['kind']=='garden' and mi in protected:assert a==b,after['name']
            ac=doc['accessors'][b['indices']];view=doc['bufferViews'][ac['bufferView']]
            indices=struct.unpack_from('<'+str(ac['count'])+{5121:'B',5123:'H',5125:'I'}[ac['componentType']],
                                       new_bin,view.get('byteOffset',0)+ac.get('byteOffset',0))
            count=doc['accessors'][b['attributes']['POSITION']]['count']
            assert ac['count']%3==0 and max(indices)<count
            triangles+=len(indices)//3
    assert triangles==entry['trianglesAfter']
    reports.append({'kind':entry['kind'],'triangles':triangles,'sha256':entry['sha256'],
                    'originalBinaryPrefixPreserved':True,'contactSurfacesUnchanged':True,
                    'animations':len(doc.get('animations',[]))})
result={'passed':True,'scope':'Geometry indices are lossy; other source data unchanged. Not device visual/FPS acceptance.','models':reports}
(folder/'geometry-verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
