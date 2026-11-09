"""Fetch a bounded set of CC0 production assets from the publisher's download CDN."""
import concurrent.futures
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets-src/emerald-forest-v2/sources'
ASSETS={'fern_02':['fern_02_alpha_1k.png'],'rock_moss_set_01':[]}


def fetch_asset(name):
    out=OUT/name
    out.mkdir(parents=True,exist_ok=True)
    files=[]
    def get(relative,url):
        path=(out/relative).resolve()
        assert path.is_relative_to(out.resolve())
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            with urllib.request.urlopen(url,timeout=90) as response:
                data=response.read()
            path.write_bytes(data)
        data=path.read_bytes()
        files.append(dict(file=relative,url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
        return data
    base='https://dl.polyhaven.org/file/ph-assets/Models'
    relative=name+'_1k.gltf'
    doc=json.loads(get(relative,f'{base}/gltf/1k/{name}/{relative}'))
    for item in doc.get('buffers',[])+doc.get('images',[]):
        uri=item.get('uri','')
        if not uri or uri.startswith('data:'):continue
        if uri.endswith('.bin'):
            url=f'{base}/gltf/8k/{name}/{Path(uri).name}'
        else:
            url=f'{base}/jpg/1k/{name}/{Path(uri).name}'
        get(uri,url)
    for alpha in ASSETS[name]:
        get('textures/'+alpha,f'{base}/png/1k/{name}/{alpha}')
    (out/'SOURCE.json').write_text(json.dumps(dict(
        asset=name,source='https://polyhaven.com/a/'+name,license='CC0',
        licenseURL='https://polyhaven.com/license',files=files),indent=2))
    print(name,sum(x['bytes'] for x in files),flush=True)


def fetch_forest_floor():
    # Keep publisher URLs/hashes in the same manifest as the model sources.
    folder=OUT/'forest_leaves_02'
    manifest=json.loads((folder/'SOURCE.json').read_text(encoding='utf8'))
    for entry in manifest['files']:
        path=folder/entry['file']
        if not path.exists():
            request=urllib.request.Request(entry['url'],headers={'User-Agent':'BugWorld asset authoring'})
            with urllib.request.urlopen(request,timeout=90) as response:
                path.write_bytes(response.read())
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'], path


if __name__=='__main__':
    fetch_forest_floor()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(fetch_asset,ASSETS))
    files=[]
    for name,url in [
        ('forest_slope.jpg','https://dl.polyhaven.org/file/ph-assets/HDRIs/extra/Tonemapped%20JPG/forest_slope.jpg'),
        ('forest_slope_4k.exr','https://dl.polyhaven.org/file/ph-assets/HDRIs/exr/4k/forest_slope_4k.exr')]:
        path=OUT/name
        if not path.exists():
            urllib.request.urlretrieve(url,path)
        files.append(dict(file=name,url=url,bytes=path.stat().st_size,
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (OUT/'forest_slope_SOURCE.json').write_text(json.dumps(dict(
        license='CC0-1.0',source='https://polyhaven.com/a/forest_slope',
        author='Andreas Mischok',files=files),indent=2))
