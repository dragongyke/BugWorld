"""Exercise real PICO semantic UI actions without saving/deleting user artwork.

Requires ROM `uiautomator spatial`. This checks callbacks and resulting UI state;
it does not claim to emulate tracked fingers or measure compositor frame rate.
"""
import argparse
import atexit
import json
import subprocess
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--adb', default='C:/PICO4Overseas/platform-tools-latest-windows/platform-tools/adb.exe')
parser.add_argument('--out', default='.work/studio107-device.json')
parser.add_argument('--stage', action='store_true')
args = parser.parse_args()
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
package = 'com.bugworld.app'
checks = []
successful = False

def report():
    result = {'package': package, 'status': 'passed' if successful else 'incomplete', 'checks': checks,
              'limits': 'Semantic actions and UI state only; tracked finger input, panel following, and visual frame pacing require headset observation.'}
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result

atexit.register(report)

def adb(*parts):
    return subprocess.check_output([args.adb, *parts], encoding='utf-8', timeout=70).strip()

def snapshot():
    result = json.loads(adb('shell', 'uiautomator', 'spatial', 'snapshot', '--package', package, '--max-nodes', '500'))
    if result.get('error', {}).get('code') == 'TARGET_ROOT_TIMEOUT':
        return {'nodes': [], 'windows': []}
    assert result['ok'] and not result['truncated'], result
    return result

def labels(ui):
    return {value for node in ui['nodes'] for value in (node.get('text'), node.get('contentDescription')) if value}

def wait_for(label, timeout=30):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        ui = snapshot()
        if label in labels(ui):
            return ui
        time.sleep(.3)
    raise AssertionError(f'UI did not show {label}')

def click_target(label, ui):
    by_id = {node['id']: node for node in ui['nodes']}
    matches = [node for node in ui['nodes'] if label in (node.get('text'), node.get('contentDescription'))]
    for node in matches:
        while node:
            if node['enabled'] and any(action['id'] == 16 for action in node['actions']):
                return node
            node = by_id.get(node['parentNodeId'])

def click(label, ui=None):
    until = time.monotonic() + 20
    while time.monotonic() < until:
        node = click_target(label, ui or snapshot())
        if node:
            result = json.loads(adb('shell', 'uiautomator', 'spatial', 'action', '--package', package,
                                    '--node-id', node['id'], '--action-id', '16'))
            if result.get('error', {}).get('code') == 'STALE_NODE':
                ui = None
                continue
            assert result['ok'] and result['performed'], result
            return
        ui = None
        time.sleep(.3)
    raise AssertionError(f'No enabled click target: {label}')

ui = wait_for('新画纸')
if '收起预览' in labels(ui):
    click('收起预览', ui)
    ui = wait_for('看看它')
paper = next(node for node in ui['nodes'] if node.get('contentDescription') == '昆虫涂色画纸')
bar = next(node for node in ui['nodes'] if node.get('contentDescription') == 'BugWorld 画纸')
roots = {node['windowId']: node for node in ui['nodes'] if node['parentNodeId'] is None}
def width(node):
    bounds = node['boundsInScreen']
    return bounds['right'] - bounds['left']
ratio = width(roots[bar['windowId']]) / width(roots[paper['windowId']])
assert ratio < .8, ratio
checks.append({'test': 'compact_native_bar', 'barToPaperWidth': ratio})

click('新画纸', ui)
ui = wait_for('换一张新画纸？')
click('取消', ui)
assert '换一张新画纸？' not in labels(snapshot())
checks.append({'test': 'new_paper_opens_confirmation_and_cancel_preserves_drawing', 'passed': True})

click('看看它')
ui = wait_for('捏合拖动转一转 · 轻触和它打招呼')
ui = wait_for('收起预览')
click('新画纸', ui)
click('取消', wait_for('换一张新画纸？'))
click('收起预览')
wait_for('看看它')
checks.append({'test': 'preview_and_board_controls_while_preview_visible', 'passed': True})

for label in ['独角仙', '瓢虫', '毛毛虫', '蝴蝶']:
    click(label)
    ui = snapshot()
    paper = next(node for node in ui['nodes'] if node.get('contentDescription') == '昆虫涂色画纸')
    assert any(node.get('text') == label and node['windowId'] == paper['windowId'] for node in ui['nodes'])
checks.append({'test': 'all_four_species_show_correct_paper_title', 'passed': True})

click('作品册')
ui = wait_for('关闭作品册')
click('关闭作品册', ui)
checks.append({'test': 'album_opens_and_closes', 'passed': True})

if args.stage:
    click('去花园')
    wait_for('回到画板', timeout=70)
    # Wait for scene readiness; the return button alone is not proof that the garden loaded.
    deadline = time.monotonic() + 70
    while time.monotonic() < deadline:
        ui = snapshot()
        text = ' '.join(str(item) for item in labels(ui))
        if '花园在等你画出' in text or '伸出手指或摊开手掌' in text:
            break
        time.sleep(.5)
    else:
        raise AssertionError('Stage never became ready')
    click('回到画板', ui)
    wait_for('新画纸', timeout=30)
    click('新画纸')
    click('取消', wait_for('换一张新画纸？'))
    checks.append({'test': 'stage_ready_return_and_board_input', 'passed': True})

successful = True
print(json.dumps(report(), ensure_ascii=False))
