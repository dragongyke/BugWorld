"""Check portable native dependencies and measured editor water animation.

These checks cannot accept artistic fidelity, Android rendering or frame time.
Image data is read for measurement only; screenshots are never altered.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT/'assets-src/emerald-native-scene'
IMAGES = ROOT/'assets-src/emerald-forest-v2'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bundle',type=Path,help='Optional rebuilt review bundle to compare with the recorded pack hash')
args=parser.parse_args()
snapshot = json.loads((PROJECT/'snapshot-report.json').read_text())
references = 0
texts = []
for entry in snapshot['files']:
    path = PROJECT/entry['path']
    assert path.is_file(), path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], path
    if path.suffix == '.usda':
        text = path.read_text(encoding='utf8')
        texts.append(text)
        for value in re.findall(r'@([^@\r\n]+)@', text):
            assert not re.match(r'^[A-Za-z]:|^/|https?://', value), value
            target = (path.parent/value).resolve()
            assert target.is_relative_to(PROJECT.resolve()) and target.is_file(), target
            references += 1
all_text = '\n'.join(texts)
assert 'DirectionalLightComponent' in all_text
assert 'DynamicShadowComponent' in all_text and re.search(r'bool CastsShadow = (?:false|0)\b', all_text)
assert 'midground_forest_bark' not in all_text
assert 'ND_time_float' in all_text
assert 'ND_extract_color4' in all_text

frames = [np.asarray(Image.open(IMAGES/f'editor-water-native-t{i}.png').convert('RGB'),dtype=np.float32) for i in (0,1)]
assert frames[0].shape == frames[1].shape
height, width = frames[0].shape[:2]
regions = {'water':(.02,.72,.22,.94),'staticBackground':(.35,.02,.55,.12)}
motion = {}
for name,(x0,y0,x1,y1) in regions.items():
    diff = np.abs(frames[0][int(y0*height):int(y1*height),int(x0*width):int(x1*width)]-
                  frames[1][int(y0*height):int(y1*height),int(x0*width):int(x1*width)])
    motion[name] = dict(normalizedRoi=[x0,y0,x1,y1],meanAbsoluteRgbDelta=float(diff.mean()),
                        fractionPixelsDeltaAbove3=float((diff.max(axis=2)>3).mean()))
assert motion['water']['meanAbsoluteRgbDelta'] > .5, motion
assert motion['staticBackground']['meanAbsoluteRgbDelta'] < .1, motion
pack = json.loads((PROJECT/'pack-report.json').read_text())
assert pack['exitCode'] == 0
bundle_verified=False
if args.bundle:
    assert hashlib.sha256(args.bundle.read_bytes()).hexdigest() == pack['bundleSha256']
    bundle_verified=True
views = []
for name in ('front','right','back','left','seated','canopy'):
    path = IMAGES/f'editor-native-{name}-final.png'
    with Image.open(path) as image:
        image.verify()
    views.append(dict(view=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
result = dict(status='passed',dependencyFiles=len(snapshot['files']),relativeReferences=references,
              waterMotion=motion,editorViews=views,bundleSha256=pack['bundleSha256'],
              bundleVerifiedThisRun=bundle_verified,headsetVerified=False,performanceMeasured=False,
              scope='Portable references, native component declarations and recorded fixed-camera pixel motion. Bundle verification is optional and reported separately; no Android/GPU acceptance.')
report=ROOT/'.work/emerald-native-verification.json';report.parent.mkdir(exist_ok=True)
report.write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
