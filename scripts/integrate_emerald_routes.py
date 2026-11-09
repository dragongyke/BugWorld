"""Install the verified route data with its matching native scene revision."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'assets-src/emerald-routes'
manifest=json.loads((folder/'routes.json').read_text())
assert manifest['sourceGlbSha256']==hashlib.sha256((ROOT/'assets-src/emerald-forest-v2/garden.glb').read_bytes()).hexdigest()
assert len(manifest['routes'])==19 and max(r['maxGapMetres'] for r in manifest['routes'])<.003
target=ROOT/'app/src/main/java/com/bugworld/app/garden/ApprovedGardenRoutes.kt'
text=target.read_text(encoding='utf8')
start=text.index('    // BEGIN GENERATED SURFACE KNOTS')
end=text.index('    // END GENERATED SURFACE KNOTS',start)+len('    // END GENERATED SURFACE KNOTS')
text=text[:start]+(folder/'route-knots.kt').read_text().rstrip()+text[end:]
target.write_text(text,encoding='utf8')
shutil.copy2(folder/'routes.json',ROOT/'app/src/main/assets/v3/environment/garden-routes.json')
print('Installed 19 surface-sampled resident routes')
