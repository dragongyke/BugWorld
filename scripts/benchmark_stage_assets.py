"""Desktop warm-cache loader proxies only. Not Android native GLB or GPU upload timing."""
import argparse
import io
import json
import statistics
import struct
import time
from pathlib import Path
from PIL import Image

def sample(path):
    start=time.perf_counter(); cpu=time.process_time()
    raw=path.read_bytes(); read=time.perf_counter()
    length=struct.unpack_from('<I',raw,12)[0]
    doc=json.loads(raw[20:20+length]); parsed=time.perf_counter()
    binary=memoryview(raw)[28+length:]
    for image in doc.get('images',[]):
        view=doc['bufferViews'][image['bufferView']]; offset=view.get('byteOffset',0)
        with Image.open(io.BytesIO(binary[offset:offset+view['byteLength']])) as pixels:
            pixels.load()
    end=time.perf_counter()
    return dict(fileReadMs=(read-start)*1000,jsonParseMs=(parsed-read)*1000,
                embeddedImageDecodeMs=(end-parsed)*1000,totalWallMs=(end-start)*1000,
                processCpuMs=(time.process_time()-cpu)*1000)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--candidate',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); results={}
    for label,path in [('baseline',args.baseline),('candidate',args.candidate)]:
        sample(path) # Explicit warmup; this is not a cold disk benchmark.
        rows=[sample(path) for _ in range(5)]
        results[label]=dict(samples=rows,median={key:statistics.median(r[key] for r in rows) for key in rows[0]})
    report=dict(scope='Desktop Python/Pillow warm-cache proxy, 1 warmup + 5 samples each. JSON parsing excludes mesh processing. '
                      'No native GLB parsing, Android texture upload, headset GPU, draw-call or FPS measurement.',results=results)
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({key:value['median'] for key,value in results.items()},indent=2))
