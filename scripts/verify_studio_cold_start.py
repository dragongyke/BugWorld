"""Device regression: cold launches retain an accessible paper and independent tools.

Requires an awake/worn headset. Restarts the app without clearing saved works;
each launch intentionally starts a fresh paper. Semantic presence is not visual proof.
"""
import argparse
import datetime as dt
import json
import subprocess
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--adb', default='C:/PICO4Overseas/platform-tools-latest-windows/platform-tools/adb.exe')
parser.add_argument('--cycles', type=int, default=3)
parser.add_argument('--out', default='.work/studio-cold-start-regression.json')
args = parser.parse_args()
package = 'com.bugworld.app'
checks = []
last_snapshot = None


def shell(*parts):
    return subprocess.check_output([args.adb, 'shell', *parts], encoding='utf-8', timeout=25)


def snapshot():
    global last_snapshot
    last_snapshot = json.loads(shell('uiautomator', 'spatial', 'snapshot', '--package', package, '--max-nodes', '500'))
    return last_snapshot


def require_awake():
    power = shell('dumpsys', 'power')
    if 'mWakefulness=Awake' not in power:
        raise RuntimeError('Headset is not awake; no cold-start result can be recorded.')


def labelled(node, text):
    return text in (node.get('text'), node.get('contentDescription'))


def wait_paper():
    deadline = time.monotonic() + 18
    while time.monotonic() < deadline:
        ui = snapshot()
        if ui.get('ok') and all(any(labelled(n, label) and n.get('visibleToUser')
                                   for n in ui['nodes'])
                               for label in ('SpatialView', '昆虫涂色画纸', '去花园', '看看它', '画具面板')):
            view = next(n for n in ui['nodes'] if labelled(n, 'SpatialView'))
            paper = next(n for n in ui['nodes'] if labelled(n, '昆虫涂色画纸'))
            # The temporary ordinary canvas is replaced on first resume. Never
            # send a semantic action to that soon-to-be-disposed composition.
            if view['windowId'] != paper['windowId']:
                return ui
        time.sleep(.4)
    raise AssertionError(f'Paper or its actions/tools missing: {ui.get("error", ui.get("windows"))}')


def click(text):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        ui = snapshot()
        assert ui.get('ok'), ui
        nodes = {n['id']: n for n in ui['nodes']}
        target = next((n for n in ui['nodes'] if labelled(n, text)), None)
        while target and not any(a['id'] == 16 for a in target['actions']):
            target = nodes.get(target['parentNodeId'])
        if not target or not target['enabled']:
            time.sleep(.3)
            continue
        result = json.loads(shell('uiautomator', 'spatial', 'action', '--package', package,
                                  '--node-id', target['id'], '--action-id', '16'))
        if result.get('performed'):
            return
        if result.get('error', {}).get('code') != 'STALE_NODE':
            raise AssertionError(result)
    raise AssertionError(f'Click target unavailable or stale: {text}')


try:
    for cycle in range(args.cycles):
        require_awake()
        shell('am', 'force-stop', package)
        shell('am', 'start', '-n', package + '/.platform.LaunchActivity')
        paper_ui = wait_paper()
        click('作品册')
        wait_paper()
        click('关闭作品册')
        wait_paper()
        checks.append({'coldStart': cycle + 1, 'paperAndButtons': True,
                       'albumOpenCloseKeepsPaper': True,
                       'initialWindowCount': len(paper_ui.get('windows', [])),
                       'checkedUTC': dt.datetime.now(dt.timezone.utc).isoformat()})
        print(json.dumps(checks[-1]), flush=True)
    result = {'status': 'passed', 'checks': checks}
except Exception as error:
    result = {'status': 'failed', 'checks': checks, 'error': repr(error)}
    if last_snapshot is not None:
        Path(args.out).with_suffix('.last-snapshot.json').write_text(
            json.dumps(last_snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
    raise
finally:
    result['limits'] = 'Semantic presence/actions only; headset observation still required. No saved work is deleted.'
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
