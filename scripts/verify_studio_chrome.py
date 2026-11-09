"""Check independent native tab targets and full-width tools on the connected headset.

Optional semantic clicks switch papers without saving/deleting artwork. Visual gaze
isolation and the 3D panel angle still require headset observation.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--adb', default='C:/PICO4Overseas/platform-tools-latest-windows/platform-tools/adb.exe')
parser.add_argument('--out', default='.work/studio108-chrome.json')
parser.add_argument('--exercise', action='store_true')
args = parser.parse_args()
package = 'com.bugworld.app'
species = ['蝴蝶', '独角仙', '瓢虫', '毛毛虫']
checks = []

def command(*parts):
    return json.loads(subprocess.check_output([args.adb, 'shell', 'uiautomator', 'spatial', *parts], encoding='utf-8', timeout=35))

def snapshot():
    result = command('snapshot', '--package', package, '--max-nodes', '500')
    assert result['ok'] and not result['truncated'], result
    return result

def label(node, value):
    return value in (node.get('text'), node.get('contentDescription'))

def targets(ui):
    nodes = ui['nodes']
    index = {node['id']: node for node in nodes}
    bar_id = next(node['windowId'] for node in nodes if label(node, 'BugWorld 画纸'))
    result = {}
    for name in species:
        node = next(node for node in nodes if node['windowId'] == bar_id and label(node, name))
        clickable = []
        while node:
            if node['enabled'] and any(action['id'] == 16 for action in node['actions']):
                clickable.append(node)
            node = index.get(node['parentNodeId'])
        assert len(clickable) == 1, f'{name}: expected one click owner, got {len(clickable)}'
        result[name] = clickable[0]
    assert len({node['id'] for node in result.values()}) == len(species), 'Species share a click owner'
    return result

try:
    ui = snapshot()
    targets(ui)
    checks.append({'test': 'one_distinct_click_owner_per_species', 'passed': True})
    roots = {node['windowId']: node for node in ui['nodes'] if node['parentNodeId'] is None}
    panel = next(node for node in ui['nodes'] if label(node, '画具面板'))
    body, outer = panel['boundsInScreen'], roots[panel['windowId']]['boundsInScreen']
    assert all(abs(body[key] - outer[key]) <= 2 for key in ('left', 'right', 'top', 'bottom')), (body, outer)
    checks.append({'test': 'tools_fill_native_subwindow', 'passed': True, 'contentBounds': body, 'windowBounds': outer})
    if args.exercise:
        for name in [*species[1:], species[0]]:
            clicked = False
            for attempt in range(3):
                node = targets(snapshot())[name]
                action = command('action', '--package', package, '--node-id', node['id'], '--action-id', '16')
                if action.get('error', {}).get('code') == 'STALE_NODE':
                    continue
                assert action['ok'] and action['performed'], action
                clicked = True
                break
            assert clicked, f'{name}: target stayed stale'
            for attempt in range(15):
                ui = snapshot()
                assert not any(label(node, '选择画纸') for node in ui['nodes']), f'{name} opened picker'
                paper_id = next(node['windowId'] for node in ui['nodes'] if label(node, '昆虫涂色画纸'))
                if any(node['windowId'] == paper_id and node.get('text') == name for node in ui['nodes']):
                    break
                time.sleep(.2)
            else:
                raise AssertionError(f'{name}: board did not switch')
            checks.append({'test': 'direct_paper_switch', 'species': name, 'passed': True})
    result = {'status': 'passed', 'checks': checks}
except Exception as error:
    result = {'status': 'failed', 'checks': checks, 'error': str(error)}
    raise
finally:
    result['limits'] = 'Semantic hierarchy/actions only; gaze visuals and inward panel angle require headset observation.'
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))
