"""Compile the portable native scene with the SDK's mobile shader target."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT/'assets-src/emerald-native-scene'
SDK = Path(os.environ['LOCALAPPDATA'])/'pico/6.1/editor'
OUTPUT = PROJECT/'Build/EmeraldForestReview.bundle'
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env['PATH'] = str(SDK/'SpatialEditor') + os.pathsep + env['PATH']
command = [str(SDK/'spatialbundle/spatialbundle.exe'),'pack',
    '--project-dir',str(PROJECT),'--scene-dir',str(PROJECT/'Sources/Scenes'),
    '--scene-files',str(PROJECT/'Sources/Scenes/Hi.usda'),
    '--output-bundle',str(OUTPUT),'--formats','usda','--override-output',
    '--compress-textures','--discard-unused-resources','--preserve-resources','material',
    '--material-platform','mobile','--force-build']
start = time.monotonic()
result = subprocess.run(command,cwd=PROJECT,env=env,capture_output=True,timeout=300)
(PROJECT/'pack-output.log').write_bytes(result.stdout+result.stderr)
report = dict(exitCode=result.returncode,durationSeconds=round(time.monotonic()-start,3),
    bundleBytes=OUTPUT.stat().st_size if OUTPUT.exists() else 0,
    bundleSha256=hashlib.sha256(OUTPUT.read_bytes()).hexdigest() if OUTPUT.exists() else None,
    command=command,environmentWorkaround='Same SDK editor DLL directory added to child PATH only',
    scope='Portable native scene mobile compilation. Review insects are static poses; no APK install, headset or FPS evidence.')
(PROJECT/'pack-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
if result.returncode:
    print((result.stdout+result.stderr).decode('utf8','replace')[-5000:])
raise SystemExit(result.returncode)
