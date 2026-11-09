"""Download selected public CC0 source assets and verify publisher hashes."""
import concurrent.futures
import hashlib
import json
import urllib.request
from pathlib import Path

OUT=Path(__file__).resolve().parents[1]/'assets-src/v3-review/garden/sources'
ITEMS=[('dead_tree_trunk_02','2k'),('tree_stump_01','2k'),('moss_01','1k'),('dead_tree_trunk','2k')]

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'BugWorld asset review (CC0 source retrieval)'})
    with urllib.request.urlopen(req,timeout=45) as response:return response.read()

def one(item):
    name,res=item;target=OUT/name;target.mkdir(parents=True,exist_ok=True)
    cache=target/'publisher-files.json'
    metadata=json.loads(cache.read_text(encoding='utf8')) if cache.exists() else json.loads(get('https://api.polyhaven.com/files/'+name))
    (target/'publisher-files.json').write_text(json.dumps(metadata,indent=2),encoding='utf8')
    config=metadata['gltf'][res]['gltf']; files={name+'_'+res+'.gltf':config,**config['include']}
    if name=='moss_01':
        alpha='textures/moss_01_alpha_1k.png'
        files[alpha]=metadata['blend'][res]['blend']['include'][alpha]
    hashes={}
    for relative,entry in files.items():
        path=(target/relative).resolve()
        assert path.is_relative_to(target.resolve())
        path.parent.mkdir(parents=True,exist_ok=True)
        data=path.read_bytes() if path.exists() else get(entry['url'])
        assert hashlib.md5(data).hexdigest()==entry['md5'],relative
        path.write_bytes(data);hashes[relative]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'url':entry['url']}
        print(name,relative,len(data),flush=True)
    (target/'SOURCE.json').write_text(json.dumps({'name':name,'resolution':res,'license':'CC0','source':'https://polyhaven.com/a/'+name,'licenseURL':'https://polyhaven.com/license','files':hashes},indent=2),encoding='utf8')
    return name

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(one,ITEMS):print('Verified',result,flush=True)
