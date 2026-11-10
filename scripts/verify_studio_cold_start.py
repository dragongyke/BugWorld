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
parser.add_argument('--current-only', action='store_true', help='Inspect the current failure without restarting the app')
parser.add_argument('--transitions', action='store_true', help='Also verify preview controls and Stage return with/without album')
parser.add_argument('--stage-only', action='store_true', help='Verify Stage return without repeating preview checks')
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
    translations = {'昆虫涂色画纸': 'Insect coloring sheet', '去花园': 'Visit garden',
                    '看看它': 'See it in 3D', '画具面板': 'Art tools panel',
                    '作品册': 'Album', '关闭作品册': 'Close album',
                    '收起预览': 'Hide preview', '新画纸': 'New sheet',
                    '换一张新画纸？': 'Start a new sheet?', '取消': 'Cancel',
                    '回到画板': 'Back to canvas', '独角仙': 'Rhino beetle'}
    return any(label in (node.get('text'), node.get('contentDescription'))
               for label in (text, translations.get(text, text)))


def wait_paper():
    deadline = time.monotonic() + 18
    while time.monotonic() < deadline:
        require_awake()
        ui = snapshot()
        if ui.get('ok') and all(any(labelled(n, label) and n.get('visibleToUser')
                                   for n in ui['nodes'])
                               for label in ('昆虫涂色画纸', '去花园', '看看它', '画具面板')):
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


def wait_label(label, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        require_awake()
        ui = snapshot()
        if any(labelled(n, label) and n['visibleToUser'] for n in ui.get('nodes', [])):
            return ui
    raise AssertionError('Missing visible control: ' + label)


def check_preview():
    click('看看它')
    # An ordinary fallback canvas also contains Hide preview. Require a separate native paper root.
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        ui = wait_label('收起预览')
        spatial = next((n for n in ui['nodes'] if labelled(n, 'SpatialView')), None)
        papers = [n for n in ui['nodes'] if labelled(n, '昆虫涂色画纸')]
        if spatial and len(papers) == 1 and papers[0]['windowId'] != spatial['windowId']:
            break
    else:
        raise AssertionError('Preview never acquired its native paper surface')
    click('新画纸'); wait_label('换一张新画纸？'); click('取消')
    wait_label('收起预览')
    click('独角仙')
    wait_paper()
    checks.append({'previewNativePaperAndButtons': True, 'speciesChangeReturnsEditor': True})
    print(json.dumps(checks[-1]), flush=True)


def check_stage_returns():
    for with_album in (False, True):
        if with_album:
            click('作品册'); wait_label('关闭作品册')
        def ready_count():
            return shell('logcat', '-d', '-s', 'BugWorldStagePerf:I').count('phase=first_visible_ready')
        before = ready_count()
        click('去花园')
        wait_label('回到画板', timeout=60)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            require_awake()
            if ready_count() > before:
                break
            time.sleep(.5)
        else:
            raise AssertionError('Stage did not report first visible frames')
        click('回到画板')
        ui = wait_paper()
        if with_album:
            wait_label('关闭作品册'); click('关闭作品册'); wait_paper()
        else:
            assert not any(labelled(n, '关闭作品册') for n in ui['nodes'])
        checks.append({'stageReturn': True, 'albumPreviouslyOpen': with_album, 'albumStateRestored': True})
        print(json.dumps(checks[-1]), flush=True)


try:
    if args.current_only:
        require_awake()
        wait_paper()
    for cycle in range(args.cycles):
        if args.current_only:
            break
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
    if args.transitions:
        check_preview()
    if args.transitions or args.stage_only:
        check_stage_returns()
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
