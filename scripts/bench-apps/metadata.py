#!/usr/bin/env python3
"""Save compiler identities, input revisions and runner details with the raw results."""
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

work = Path(sys.argv[1])
results = work / 'results'
results.mkdir(parents=True, exist_ok=True)


def command(*args: str, cwd: Path | None = None) -> str:
    try:
        run = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    except OSError:
        return 'unavailable (failed to launch)'
    return run.stdout.strip() if run.returncode == 0 else f'unavailable (exit {run.returncode})'


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


nm = work / 'node_modules'
tools = {
    'tsc7': nm / '@typescript/typescript-linux-x64/lib/tsc',
    'tsc-rs': nm / '@tsc-rs/linux-x64/lib/tsc',
    'tsc-ts': nm / '@tsc-ts/linux-x64-gnu/lib/tsc-ts',
    'tsrs': nm / '@tsrs/linux-x64-gnu/tsrs',
    'bun': nm / 'bun/bin/bun.exe',
}
metadata = {
    'date': datetime.now(timezone.utc).isoformat(),
    'source': command('git', 'rev-parse', 'HEAD'),
    'run': f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}",
    'build': 'official npm packages',
    'host': platform.platform(),
    'cpu': command('lscpu'),
    'memory': Path('/proc/meminfo').read_text() if Path('/proc/meminfo').exists() else None,
    'node': command('node', '--version'),
    'pnpm': command('pnpm', '--version'),
    'hyperfine': command('hyperfine', '--version'),
    'rounds': int(os.environ.get('RUNS', '5')),
    'warmups': 1,
    'tools': {name: {'version': command(str(path), '--version'),
                     'sha256': digest(path)} for name, path in tools.items() if path.exists()},
    'inputs': {},
    'packages': {},
}
for repo in sorted((work / 'repos').glob('*')):
    if not (repo / '.git').exists():
        continue
    locks = {str(path.relative_to(repo)): digest(path) for path in
             [repo / 'pnpm-lock.yaml', repo / 'yarn.lock', repo / 'package-lock.json'] if path.exists()}
    metadata['inputs'][repo.name] = {'commit': command('git', 'rev-parse', 'HEAD', cwd=repo), 'locks': locks}
for name in ['typescript', 'ts6', 'tsc-rs', 'tsc-ts', 'tsrs', 'bun']:
    path = nm / name / 'package.json'
    if path.exists():
        package = json.loads(path.read_text())
        metadata['packages'][package['name'] + (' (ts6)' if name == 'ts6' else '')] = package['version']
for name in ['package-lock.json']:
    path = work / name
    metadata[name] = digest(path)
case = os.environ.get('BENCH_CASE')
(results / (f'metadata-{case}.json' if case else 'metadata.json')).write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
