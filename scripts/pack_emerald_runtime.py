"""Build the reviewed forest without its static display insects."""
from pathlib import Path
import hashlib,json,os,re,subprocess,time

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets-src/emerald-native-scene'
PROJECT=ROOT/'.work/emerald-runtime'
SCENE=PROJECT/'Sources/Scenes/Forest.usda'
OUT=ROOT/'app/src/main/assets/v3/environment/forest.bundle'
SCENE.parent.mkdir(parents=True,exist_ok=True)
source=(SOURCE/'Sources/Scenes/Hi.usda').read_text(encoding='utf8')
start=source.index('    def Xform "review_insects"')
end=source.index('    def Xform "garden"',start)
assert source.count('    def Xform "review_insects"')==1
scene=(source[:start]+source[end:]).replace('"ForestBackdrop", "review_insects", "garden"','"ForestBackdrop", "garden"')
assert 'review_insects' not in scene
scene=re.sub(r'@([^@\r\n]+)@',lambda m:'@'+(SOURCE/'Sources/Scenes'/m[1]).resolve().as_posix()+'@',scene)
SCENE.write_text(scene,encoding='utf8')
(PROJECT/'emerald_runtime.spatialproject').write_text('{"projectName":"emerald_runtime","version":"6.1.1"}',encoding='utf8')
sdk=Path(os.environ['LOCALAPPDATA'])/'pico/6.1/editor'
env=os.environ.copy();env['PATH']=str(sdk/'SpatialEditor')+os.pathsep+env['PATH']
command=[str(sdk/'spatialbundle/spatialbundle.exe'),'pack','--project-dir',str(PROJECT),
         '--scene-dir',str(SCENE.parent),'--scene-files',str(SCENE),'--output-bundle',str(OUT),
         '--formats','usda','--override-output','--compress-textures','--discard-unused-resources',
         '--material-platform','mobile','--force-build']
started=time.monotonic()
process=subprocess.run(command,cwd=PROJECT,env=env,capture_output=True,timeout=300)
(PROJECT/'pack.log').write_bytes(process.stdout+process.stderr)
if process.returncode: raise RuntimeError((process.stdout+process.stderr).decode('utf8','replace')[-5000:])
report=dict(exitCode=process.returncode,seconds=round(time.monotonic()-started,3),
            sourceSceneSha256=hashlib.sha256(source.encode()).hexdigest(),
            runtimeSceneSha256=hashlib.sha256(scene.encode()).hexdigest(),
            staticReviewInsectsRemoved=True,bundle=OUT.relative_to(ROOT).as_posix(),
            bytes=OUT.stat().st_size,sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),
            sceneName='Forest',command=command)
(ROOT/'docs/Stage-112-Bundle.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
