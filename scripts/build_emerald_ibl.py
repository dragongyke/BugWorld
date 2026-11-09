"""Filter the matching captured HDR for Android's existing KTX IBL path."""
from pathlib import Path
import hashlib,json,math
import numpy as np
import assets_v3_environment as ibl
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'assets-src/emerald-forest-v2/sources/forest_slope_4k.exr'
linear=np.load(ROOT/'.work/emerald-hdr/forest-hdr.npy')
ibl.self_test()
levels=[ibl.cube_base(linear,ibl.SIZE)]
sh=ibl.diffuse_sh(levels[0])
for index in range(1,ibl.LEVELS):
    print('HDR GGX mip',index,flush=True)
    roughness=1-math.sqrt(1-index/(ibl.LEVELS-1))
    levels.append(ibl.ggx_prefilter(linear,ibl.SIZE>>index,roughness,ibl.SAMPLES*2**max(0,index-1)))
target=ROOT/'app/src/main/assets/v3/environment/forest.ktx'
digest=hashlib.sha256(source.read_bytes()).hexdigest()
ibl.write_ktx(target,levels,sh,digest,source_range='Captured scene-linear Forest Slope EXR; no tone mapping')
result=ibl.validate(target,digest,max_linear=None)
(ROOT/'docs/Stage-112-IBL.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('HDR KTX',target,target.stat().st_size,flush=True)
