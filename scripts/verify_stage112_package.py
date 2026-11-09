"""Verify the delivered APK contents against reviewed assets and native build reports."""
import argparse,hashlib,json,math,os,re,shutil,subprocess,xml.etree.ElementTree as ET,zipfile
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
asset=ROOT/'app/src/main/assets/v3'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apk',type=Path,default=ROOT/'app/build/outputs/apk/debug/app-debug.apk')
parser.add_argument('--report',type=Path,default=ROOT/'.work/garden-package-verification.json')
parser.add_argument('--publish',action='store_true',help='Explicitly replace the retained delivery APK after checking')
args=parser.parse_args();apk=args.apk.resolve()
sdk=Path(os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT') or Path(os.environ['LOCALAPPDATA'])/'Android/Sdk')
aapt=next(iter(sorted((sdk/'build-tools').glob('*/aapt2.exe'), reverse=True)))
badging=subprocess.check_output([aapt,'dump','badging',apk],encoding='utf-8')
package=re.search(r"^package: name='com\.bugworld\.app' versionCode='(\d+)' versionName='([\d.]+)'",badging,re.M)
assert package, 'Missing BugWorld package version'
version_code,version=int(package[1]),package[2]
if version_code>=13:
    assert "application-label:'BugWorld'" in badging
    assert re.search(r"^application-label-zh(?:-[^:]+)?:'我的昆虫世界'$",badging,re.M)
sha=lambda data:hashlib.sha256(data).hexdigest()
bundle=json.loads((ROOT/'docs/Stage-112-Bundle.json').read_text())
ibl=json.loads((ROOT/'docs/Stage-112-IBL.json').read_text())
assert sha((asset/'environment/forest.bundle').read_bytes())==bundle['sha256']
assert sha((asset/'environment/forest.ktx').read_bytes())==ibl['outputSHA256']
assert bundle['exitCode']==0 and bundle['staticReviewInsectsRemoved']
assert ibl['mips'][0]['linearMax']>1

old=json.loads((ROOT/'docs/Stage-111-Asset-Verification.json').read_text())
unchanged=[]
for row in old['files']:
    if row['runtime'] in ('models/garden.glb','environment/sky.png'):continue
    path=asset/row['runtime']
    assert path.is_file(),path
    assert sha(path.read_bytes())==row['sha256'],path
    unchanged.append(row['runtime'])

routes=json.loads((asset/'environment/garden-routes.json').read_text())
assert routes['sourceGlbSha256']==sha((ROOT/'assets-src/emerald-forest-v2/garden.glb').read_bytes())
route_counts=Counter(route.get('species','shared') for route in routes['routes'])
if version_code>=13:
    expected_species={'BUTTERFLY','LADYBUG','BEETLE','CATERPILLAR'}
    if version_code>=14:
        expected_species.update({'DRAGONFLY','HONEYBEE','ANT','GRASSHOPPER'})
        for slug in ('dragonfly','honeybee','ant','grasshopper'):
            for rel in (f'models/{slug}.glb',f'templates/{slug}-lines.png',f'templates/{slug}-mask.png',f'templates/{slug}-detail.png',f'ui/species/{slug}-96.png'):
                assert (asset/rel).is_file(),rel
    assert set(route_counts)==expected_species
    assert all(2<=n<=3 for n in route_counts.values())
else:
    assert len(routes['routes'])==20
for route in routes['routes']:
    if route.get('closed',True):
        assert route['samples'][0]==route['samples'][-1]
    else:
        assert route['species'] not in ('ANT','CATERPILLAR') and route['samples'][0]!=route['samples'][-1]
    assert route['maxGapMetres']<.003
    for point in route['samples']:
        assert all(math.isfinite(v) for v in point)
        assert abs(sum(v*v for v in point[3:])-1)<.001

with zipfile.ZipFile(apk) as packed:
    names=set(packed.namelist())
    for removed in ('models/garden.glb','environment/sky.png','environment/sky.ktx','environment/water-reflection.ktx'):
        assert 'assets/v3/'+removed not in names,removed
    packaged=[]
    for path in asset.rglob('*'):
        if not path.is_file():continue
        key='assets/v3/'+path.relative_to(asset).as_posix()
        assert sha(packed.read(key))==sha(path.read_bytes()),key
        packaged.append(key)
    assert packed.getinfo('assets/v3/environment/forest.bundle').compress_type==zipfile.ZIP_STORED

tests=[ET.parse(path).getroot() for path in (ROOT/'app/build/test-results/testDebugUnitTest').glob('TEST-*.xml')]
count=sum(int(t.attrib['tests']) for t in tests)
assert count>=119
assert not any(int(t.attrib['failures']) or int(t.attrib['errors']) for t in tests)
lint=ET.parse(ROOT/'app/build/reports/lint-results-debug.xml').getroot()
issues=lint.findall('issue')
assert not any(i.attrib['severity'] in ('Error','Fatal') for i in issues)
output=apk
if args.publish:
    output=ROOT/'deliverables'/f'BugWorld-{version}.apk'
    output.parent.mkdir(exist_ok=True)
    if apk!=output.resolve():shutil.copy2(apk,output)
report=dict(version=version,apk=output.relative_to(ROOT).as_posix(),bytes=output.stat().st_size,
            sha256=sha(output.read_bytes()),packagedV3Files=len(packaged),unchangedApprovedFiles=unchanged,
            bundleSha256=bundle['sha256'],iblSha256=ibl['outputSHA256'],routeCount=len(routes['routes']),routesPerSpecies=route_counts,
            maximumRouteInterpolationGapMetres=max(r['maxGapMetres'] for r in routes['routes']),
            unitTests=count,lintErrors=0,lintWarnings=sum(i.attrib['severity']=='Warning' for i in issues),
            status='Package verified. This command does not establish installation, headset appearance or performance.')
args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
