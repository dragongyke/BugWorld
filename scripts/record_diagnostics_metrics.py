"""Snapshot post-1.0.9 counters and executable CLI statements, never conversation text."""
import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSIONS = Path('C:/Users/Admin/.codex/sessions')
THREAD = '01a11a87-f8c7-7783-86ac-79ba85d89282'
INVESTIGATOR = '/root/stage110_perf_investigation'


def stamp(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))


def events(path):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue  # An active session can end with an unfinished JSONL record.


# Lex strings/comments before locating calls, so examples in tool input are not calls.
JS_TOKEN = re.compile(
    r'(?P<comment>//[^\n]*|/\*[\s\S]*?\*/)|'
    r'(?P<string>"(?:\\[\s\S]|[^"\\])*"|\'(?:\\[\s\S]|[^\'\\])*\'|`(?:\\[\s\S]|[^`\\])*`)|'
    r'(?P<word>[A-Za-z_$][\w$]*)|(?P<other>[^\s])')


def js_string(value):
    if value.startswith('"'):
        return json.loads(value)
    if value.startswith('`') and '${' in value:
        # Preserve static command names without evaluating arbitrary JavaScript.
        value = re.sub(r'\$\{[^{}]*\}', '__DYNAMIC_JS_ARGUMENT__', value)
        if '${' in value:
            raise ValueError('Nested template expression requires explicit reconciliation')
    escapes = {'n': '\n', 'r': '\r', 't': '\t', 'b': '\b', 'f': '\f', 'v': '\v', '0': '\0'}
    def replace(match):
        escaped = match.group(1)
        if escaped.startswith(('u', 'x')) and len(escaped) > 1:
            return chr(int(escaped[1:], 16))
        return escapes.get(escaped, escaped)
    return re.sub(r'\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|[\s\S])', replace, value[1:-1])


def shell_commands(payload):
    name = payload.get('name', '').split('.')[-1]
    if name == 'exec_command':
        args = payload.get('arguments', {})
        return [json.loads(args)['cmd'] if isinstance(args, str) else args['cmd']]
    if name != 'exec':
        return []
    code = payload.get('input', payload.get('arguments', ''))
    tokens = [(m.lastgroup, m.group()) for m in JS_TOKEN.finditer(code) if m.lastgroup != 'comment']
    result = []
    for index in range(len(tokens) - 5):
        if [v for _, v in tokens[index:index + 4]] != ['tools', '.', 'exec_command', '(']:
            continue
        depth = 0
        found = False
        for offset in range(index + 4, len(tokens) - 2):
            kind, value = tokens[offset]
            if kind != 'string' and value in '{[(':
                depth += 1
            elif kind != 'string' and value in '}])':
                depth -= 1
                if depth <= 0:
                    break
            if depth == 1 and value in ('cmd', '"cmd"', "'cmd'") and tokens[offset + 1][1] == ':':
                if tokens[offset + 2][0] != 'string':
                    raise ValueError('Nonliteral exec command requires explicit reconciliation')
                result.append(js_string(tokens[offset + 2][1]))
                found = True
                break
        if not found:
            raise ValueError('Exec command arguments were not an inline cmd object')
    return result


# Parse PowerShell without executing it. Here-strings and quoted documentation are
# string nodes, not CommandAst nodes. Resolve only preceding constant assignments.
POWERSHELL_PARSER = r'''
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$sources = @(ConvertFrom-Json ([Console]::In.ReadToEnd()))
$rows = [Collections.Generic.List[object]]::new()
$failures = [Collections.Generic.List[object]]::new()
function InFunction($node) {
    for ($p=$node.Parent; $null -ne $p; $p=$p.Parent) {
        if ($p -is [Management.Automation.Language.FunctionDefinitionAst]) { return $true }
    }
    return $false
}
for ($i=0; $i -lt $sources.Count; $i++) {
    $tokens=$null; $errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseInput($sources[$i],[ref]$tokens,[ref]$errors)
    if ($errors.Count) { $failures.Add(@{source=$i;count=$errors.Count}); continue }
    $assignments=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.AssignmentStatementAst]},$true))
    $commands=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst]},$true))
    foreach ($command in $commands) {
        if (InFunction $command) { continue }
        $values=@{}
        foreach ($assignment in $assignments) {
            if ($assignment.Extent.StartOffset -ge $command.Extent.StartOffset -or (InFunction $assignment)) { continue }
            if ($assignment.Left -isnot [Management.Automation.Language.VariableExpressionAst]) { continue }
            if ($assignment.Right -is [Management.Automation.Language.CommandExpressionAst] -and
                $assignment.Right.Expression -is [Management.Automation.Language.StringConstantExpressionAst]) {
                $values[$assignment.Left.VariablePath.UserPath]=$assignment.Right.Expression.Value
            }
        }
        $parts=@(foreach ($element in $command.CommandElements) {
            if ($element -is [Management.Automation.Language.StringConstantExpressionAst]) { $element.Value }
            elseif ($element -is [Management.Automation.Language.VariableExpressionAst] -and $values.ContainsKey($element.VariablePath.UserPath)) {
                $values[$element.VariablePath.UserPath]
            } else { $element.Extent.Text }
        })
        if (-not $parts.Count) { continue }
        $kind=$null; $skip=1
        $executable=$parts[0].Replace([char]92,[char]47)
        if ($executable -match '(?i)(^|/)pico-cli(?:\.ps1|\.cmd|\.exe)?$') { $kind='pico_cli' }
        elseif ($executable -match '(?i)(^|/)node(?:\.exe)?$' -and $parts.Count -gt 1 -and
            $parts[1].Replace([char]92,[char]47) -match 'profiler-cli[^/]*/package/dist/index\.js$') {
            $kind='direct_profiler'; $skip=2
        }
        elseif ($executable -like '*__DYNAMIC_JS_ARGUMENT__*') {
            $failures.Add(@{source=$i;issue='Dynamic executable requires explicit reconciliation'})
        }
        if ($kind) {
            $arguments=@($parts | Select-Object -Skip $skip)
            $rows.Add(@{source=$i;offset=$command.Extent.StartOffset;kind=$kind;arguments=$arguments})
        }
    }
}
@{rows=@($rows);errors=@($failures)} | ConvertTo-Json -Depth 8 -Compress
'''


def parse_shell_commands(commands):
    if not commands:
        return []
    powershell = shutil.which('pwsh') or shutil.which('powershell')
    if not powershell:
        raise RuntimeError('PowerShell is required to parse shell commands without executing them')
    process = subprocess.run([powershell, '-NoProfile', '-NonInteractive', '-Command', POWERSHELL_PARSER],
                             input=json.dumps(commands), text=True, encoding='utf-8', capture_output=True, check=True)
    result = json.loads(process.stdout)
    if result['errors']:
        raise ValueError(f"PowerShell parsing failed for shell source indexes: {result['errors']}")
    return result['rows']


def reconcile_inventory(rows, inventory, kind):
    def signature(arguments):
        return tuple(str(arg).replace('\\', '/').casefold() for arg in arguments)
    used = set()
    matched = supplemented = 0
    for entry in inventory.get('records', []):
        entry_kind = 'direct_profiler' if entry['launcher'] == 'node bundled perf entry' else 'pico_cli'
        if entry_kind != kind:
            continue
        wanted = signature(entry['arguments'])
        match = next((i for i, row in enumerate(rows) if i not in used and row.get('task') == INVESTIGATOR
                      and signature(row['arguments']) == wanted), None)
        if match is not None:
            used.add(match)
            rows[match]['inventorySequence'] = entry['sequence']
            matched += 1
        else:
            rows.append({'utc': None, 'task': INVESTIGATOR, 'arguments': entry['arguments'],
                         'inventorySequence': entry['sequence'], 'evidence': 'investigator execution inventory'})
            used.add(len(rows) - 1)
            supplemented += 1
    return {'matched': matched, 'supplemented': supplemented}


def build_snapshot(sessions, baseline, inventory, thread=THREAD, as_of=None):
    now = as_of or dt.datetime.now(dt.timezone.utc)
    start = stamp(baseline['snapshotUTC'])
    if now < start:
        raise ValueError('Snapshot cannot precede its baseline')
    saved = {row['log']: row for row in baseline['records']}
    records, shell, origins, warnings = [], [], [], []
    found_root = False
    for path in sorted(sessions.rglob('*.jsonl')):
        meta = next(events(path), {}).get('payload', {})
        source = meta.get('source', {})
        spawn = source.get('subagent', {}).get('thread_spawn', {}) if isinstance(source, dict) else {}
        is_root = meta.get('id') == thread
        if not is_root and spawn.get('parent_thread_id') != thread:
            continue
        found_root |= is_root
        task = '/root' if is_root else spawn.get('agent_path', 'direct_child')
        before, latest, last_utc = {}, {}, None
        seen_calls = set()
        for event in events(path):
            when = stamp(event['timestamp'])
            if when > now:
                continue
            payload = event.get('payload', {})
            if payload.get('type') == 'token_count':
                usage = (payload.get('info') or {}).get('total_token_usage')
                if usage:
                    latest, last_utc = usage, event['timestamp']
                    if when <= start:
                        before = usage
            if when <= start or event.get('type') != 'response_item' or payload.get('type') not in ('function_call', 'custom_tool_call'):
                continue
            call_id = payload.get('call_id')
            if call_id and call_id in seen_calls:
                continue
            seen_calls.add(call_id)
            try:
                commands = shell_commands(payload)
            except ValueError as error:
                warnings.append({'log': path.name, 'utc': event['timestamp'], 'issue': str(error)})
                continue
            for command in commands:
                shell.append(command)
                origins.append({'utc': event['timestamp'], 'log': path.name, 'threadId': meta.get('id'),
                                'task': task, 'callId': call_id, 'evidence': 'executed shell tool; PowerShell AST'})
        if not latest:
            continue
        base = saved.get(path.name, {}).get('cumulative', before)
        if path.name in saved:
            basis = 'Stage-109-Usage.json cumulative counter'
        elif before:
            basis = 'last counter at or before phase start'
        elif stamp(meta['timestamp']) > start:
            basis = 'new direct child after phase start; zero baseline'
        else:
            warnings.append({'log': path.name, 'issue': 'No pre-phase token baseline; excluded from token delta'})
            continue
        delta = {key: value - base.get(key, 0) for key, value in latest.items()}
        if any(value < 0 for value in delta.values()):
            warnings.append({'log': path.name, 'issue': 'Counter reset; excluded from token delta'})
        elif delta.get('total_tokens', 0):
            records.append({'log': path.name, 'threadId': meta.get('id'), 'task': task, 'asOfUTC': last_utc,
                            'baselineBasis': basis, 'baselineAsOfUTC': saved.get(path.name, {}).get('asOfUTC'),
                            'baseline': base, 'cumulative': latest, 'phase': delta})
    if not found_root:
        raise ValueError('Root session log not found; refusing an incomplete snapshot')
    cli, direct = [], []
    for row in parse_shell_commands(shell):
        item = {**origins[row['source']], 'arguments': row['arguments'], 'statementOffset': row['offset']}
        (cli if row['kind'] == 'pico_cli' else direct).append(item)
    reconciliation = {'pico_cli': reconcile_inventory(cli, inventory, 'pico_cli'),
                      'direct_profiler': reconcile_inventory(direct, inventory, 'direct_profiler')}
    totals = {}
    for row in records:
        for key, value in row['phase'].items():
            totals[key] = totals.get(key, 0) + value
    return {'threadId': thread, 'baselineFile': 'docs/Stage-109-Usage.json',
            'phaseStartUTC': start.isoformat(), 'snapshotUTC': now.isoformat(),
            'wallSeconds': round((now - start).total_seconds(), 3), 'netWorkSeconds': None,
            'phaseTokens': totals.get('total_tokens', 0), 'tokenTotals': totals,
            'historicalCoverageComplete': False, 'projectTotalTokens': None,
            'picoCliCalls': len(cli), 'cli': sorted(cli, key=lambda row: row['utc'] or ''),
            'directProfilerCalls': len(direct), 'directProfiler': sorted(direct, key=lambda row: row['utc'] or ''),
            'profilerInventoryReconciliation': reconciliation, 'records': records, 'warnings': warnings,
            'definition': 'Root plus direct children only. Subtract saved per-log cumulative counters; never add prior phase totals. '
                          'Input includes cached input; output includes reasoning. Counter boundaries use the saved as-of samples. '
                          'Wall time includes builds, device/user waits and parallel activity, not net work or network time. '
                          'CLI counts are explicit executable statements in shell tool calls, including help/failures, not success counts. '
                          'Direct profiler calls are separate; investigator inventory matches are deduplicated by arguments and source task. '
                          'No conversation text, billing estimate, or unexposed backend tokens. Historical project totals remain unknown.'}


def main():
    baseline = json.loads((ROOT / 'docs/Stage-109-Usage.json').read_text(encoding='utf-8'))
    inventory_path = ROOT / '.work/stage110-perf-command-inventory.json'
    inventory = json.loads(inventory_path.read_text(encoding='utf-8')) if inventory_path.exists() else {}
    result = build_snapshot(SESSIONS, baseline, inventory)
    if not inventory:
        result['warnings'].append({'issue': 'Investigator inventory unavailable; shell evidence only'})
    output = ROOT / 'docs/Stage-Diagnostics-Usage.json'
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('phaseStartUTC', 'snapshotUTC', 'wallSeconds', 'phaseTokens',
                                                  'picoCliCalls', 'directProfilerCalls', 'profilerInventoryReconciliation', 'warnings')}))


if __name__ == '__main__':
    main()
