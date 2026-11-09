"""Static GLB cost inventory. Primitive count is a submission proxy, never measured draw calls."""
import argparse
import collections
import hashlib
import io
import json
import struct
from pathlib import Path

from PIL import Image


def read_glb(path):
    raw = Path(path).read_bytes()
    assert raw[:4] == b'glTF' and struct.unpack_from('<I', raw, 4)[0] == 2
    size = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20+size])
    binary = raw[28+size:]
    return raw, doc, binary


def audit(path):
    raw, doc, binary = read_glb(path)
    materials = doc.get('materials', [])
    rows = []
    for node in doc.get('nodes', []):
        if 'mesh' not in node:
            continue
        mesh = doc['meshes'][node['mesh']]
        for primitive in mesh['primitives']:
            mode = primitive.get('mode', 4)
            assert mode == 4, (node.get('name'), mode)
            vertices = doc['accessors'][primitive['attributes']['POSITION']]['count']
            indices = doc['accessors'][primitive['indices']]['count'] if 'indices' in primitive else vertices
            material = materials[primitive['material']] if 'material' in primitive else {}
            rows.append(dict(node=node.get('name', ''), mesh=node['mesh'], triangles=indices//3,
                             vertices=vertices, material=material.get('name', ''),
                             alphaMode=material.get('alphaMode', 'OPAQUE'),
                             doubleSided=material.get('doubleSided', False)))
    images = []
    for item in doc.get('images', []):
        view = doc['bufferViews'][item['bufferView']]
        data = binary[view.get('byteOffset', 0):view.get('byteOffset', 0)+view['byteLength']]
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
            images.append(dict(name=item.get('name', ''), width=w, height=h, channels=len(im.getbands()),
                               encodedBytes=len(data), rgba8Bytes=w*h*4,
                               rgba8FullMipBytes=sum(max(1,w>>i)*max(1,h>>i)*4 for i in range(max(w,h).bit_length()))))
    totals = collections.defaultdict(lambda: dict(primitives=0, triangles=0, vertices=0))
    for row in rows:
        for key in ['primitives', 'triangles', 'vertices']:
            totals[row['material']][key] += 1 if key == 'primitives' else row[key]
    return dict(file=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                nodes=len(doc.get('nodes', [])), meshes=len(doc.get('meshes', [])),
                primitives=len(rows), triangles=sum(r['triangles'] for r in rows),
                vertices=sum(r['vertices'] for r in rows), materials=len(materials),
                alphaPrimitives=dict(collections.Counter(r['alphaMode'] for r in rows)),
                alphaTriangles={m:sum(r['triangles'] for r in rows if r['alphaMode']==m) for m in ['OPAQUE','MASK','BLEND']},
                textureRgba8MiB=sum(i['rgba8Bytes'] for i in images)/2**20,
                textureRgba8FullMipMiB=sum(i['rgba8FullMipBytes'] for i in images)/2**20,
                images=images, byMaterial=dict(totals), primitivesDetail=rows,
                limits='File inventory only; RGBA8 is a decode/upload estimate, not measured GPU allocation. '
                       'Primitive count excludes native batching, culling, stereo, shadow and additional passes.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('glb', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.glb)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['images','primitivesDetail']}))
