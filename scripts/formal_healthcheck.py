"""Record actual inspection time and evidence; never starts/restarts experiments."""
from pathlib import Path
import argparse
import datetime
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from host_execution import process_alive, available_memory_bytes


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp-' + str(os.getpid()))
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8', newline='\n')
    temp.replace(path)


def inspect(source):
    formal = ROOT / 'results/formal'
    resume = read_json(formal / 'desktop_resume.json')
    workflow = read_json(formal / 'execution_workflow.json')
    states = [read_json(path) for path in sorted((formal / 'groups').glob('*.json'))]
    rows = [row for state in states for row in state['rows']]
    scheduler_path = ROOT / resume['scheduling']['scheduler_status']
    scheduler = read_json(scheduler_path) if scheduler_path.exists() else {}
    process_rows = {}
    if os.name == 'nt':
        # Read only; raw command lines are checked in memory, never published.
        query = 'Get-CimInstance Win32_Process -Filter "' + ' OR '.join(
            'ProcessId=' + str(int(resume[key])) for key in ('matrix_pid', 'followthrough_pid'))
        query += '" | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress'
        raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', query],
                                      text=True, encoding='utf-8').strip()
        data = json.loads(raw) if raw else []
        if isinstance(data, dict):
            data = [data]
        process_rows = {row['ProcessId']: row for row in data}
    processes = {}
    for role, key, script in [('matrix', 'matrix_pid', 'formal_run.py'),
                              ('postprocessor', 'followthrough_pid', 'formal_followthrough.py')]:
        pid = int(resume[key])
        alive = process_alive(pid)
        command = process_rows.get(pid, {}).get('CommandLine') or ''
        matches = (str(ROOT).casefold() in command.casefold() and script in command) if os.name == 'nt' else None
        processes[role] = {'pid': pid, 'alive': alive, 'command_matches': matches}
    matrix_log = ROOT / resume['scheduling']['matrix_log']
    stderr = matrix_log.with_suffix('.stderr.log')
    status = workflow['status']
    complete_groups = sum(state['status'] == 'complete' for state in states)
    issues = []
    if status == 'waiting_for_matrix' and complete_groups < len(states):
        if not processes['matrix']['alive'] or processes['matrix']['command_matches'] is False:
            issues.append('matrix_process_missing_or_pid_reused')
        if scheduler and time.time() - scheduler['checked_unix_s'] > 60:
            issues.append('scheduler_snapshot_stale_check_cpu_and_logs')
    if status in ('waiting_for_matrix', 'postprocessing'):
        if not processes['postprocessor']['alive'] or processes['postprocessor']['command_matches'] is False:
            issues.append('postprocessor_missing_or_pid_reused')
    if status in ('analysis_error', 'matrix_incomplete'):
        issues.append(status)
    failures = sum(row['status'] != 'ok' for row in rows)
    if failures:
        issues.append('recorded_failed_points')
    if stderr.exists() and stderr.stat().st_size:
        issues.append('matrix_stderr_nonempty_review_required')
    now = datetime.datetime.now(datetime.timezone.utc)
    result = {
        'checked_utc': now.isoformat(),
        'checked_beijing': now.astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'),
        'source': source,
        'saved_physical_points': len(rows),
        'saved_sla_pairs': sum(len(row.get('reference', {})) for row in rows),
        'failed_points': failures, 'complete_groups': complete_groups,
        'total_groups': len(states), 'workflow_status': status, 'processes': processes,
        'scheduler_active': scheduler.get('active'), 'scheduler_pending': scheduler.get('pending'),
        'scheduler_age_s': round(time.time() - scheduler['checked_unix_s'], 1) if scheduler else None,
        'matrix_log_age_s': round(time.time() - matrix_log.stat().st_mtime, 1) if matrix_log.exists() else None,
        'available_physical_or_commit_gib': round(available_memory_bytes() / 1024**3, 2),
        'needs_review': issues,
        'inspection_result': 'needs_review' if issues else 'no_issue_detected',
        'action': 'read_only_inspection; no experiment started, stopped or repeated',
        'scope': 'Execution-health snapshot only, not final scientific validation or proof of continuous activity between checks.'
    }
    previous_path = formal / 'monitoring/latest.json'
    previous = read_json(previous_path) if previous_path.exists() else None
    result['new_points_since_previous_check'] = len(rows) - previous['saved_physical_points'] if previous else None
    history = formal / 'monitoring/checks.jsonl'
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')
    write_json(previous_path, result)
    entries = [json.loads(line) for line in history.read_text(encoding='utf-8').splitlines() if line]
    text = ('# 实际检查记录\n\n'
            '只有实际运行健康检查后才追加记录；自动任务处于启用状态本身不算一次检查。'
            '时间为北京时间。刷新或重新打开本文件可看到新记录。\n\n'
            '“定时自动检查”仅用于自动任务实际触发的检查；“本次对话检查”是响应用户消息时执行。'
            '历史不补造。记录间隔超过计划的5分钟，表示这里尚无对应的执行证据，不应假定已经检查。\n\n'
            '| 检查时间 | 触发方式 | 完整运行 | 新增 | 完成组 | 失败点 | 活跃任务 | 阶段 | 检查结果 |\n'
            '|---|---|---:|---:|---:|---:|---:|---|---|\n')
    for entry in reversed(entries):
        trigger = '定时自动检查' if entry['source'] == 'scheduled' else '本次对话检查'
        delta = entry['new_points_since_previous_check']
        verdict = '需进一步检查：' + ', '.join(entry['needs_review']) if entry['needs_review'] else '未发现异常；未干预计算'
        text += (f"| {entry['checked_beijing']} | {trigger} | {entry['saved_physical_points']} | "
                 f"{delta if delta is not None else '—'} | {entry['complete_groups']}/{entry['total_groups']} | "
                 f"{entry['failed_points']} | {entry['scheduler_active']} | {entry['workflow_status']} | {verdict} |\n")
    (ROOT / 'MONITORING_LOG.md').write_text(text, encoding='utf-8', newline='\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', choices=['manual', 'scheduled'], required=True)
    inspect(parser.parse_args().source)
