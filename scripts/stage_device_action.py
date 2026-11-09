"""Invoke one visible semantic action, or summarize a fresh snapshot. Does not alter artwork itself."""
import argparse,json,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--label');p.add_argument('--out',default='.work/stage109-ui.json');a=p.parse_args()
adb='C:/PICO4Overseas/platform-tools-latest-windows/platform-tools/adb.exe';package='com.bugworld.app'
def run(*cmd): return json.loads(subprocess.check_output([adb,'shell','uiautomator','spatial',*cmd],encoding='utf-8',timeout=12))
ui=run('snapshot','--package',package,'--max-nodes','500');Path(a.out).write_text(json.dumps(ui,ensure_ascii=False,indent=2),encoding='utf-8')
if not ui.get('ok'): raise RuntimeError(ui)
if a.label:
    nodes={n['id']:n for n in ui['nodes']}
    for target in ui['nodes']:
        if a.label not in [target.get('text'),target.get('contentDescription')]:continue
        while target:
            if target['enabled'] and any(x['id']==16 for x in target['actions']):
                result=run('action','--package',package,'--node-id',target['id'],'--action-id','16');print(json.dumps(result));raise SystemExit(0 if result.get('performed') else 1)
            target=nodes.get(target.get('parentNodeId'))
    raise RuntimeError('No enabled action '+a.label)
else:
    print(json.dumps(sorted({n.get('text') or n.get('contentDescription') for n in ui['nodes'] if n.get('text') or n.get('contentDescription')}),ensure_ascii=True))
