#!/usr/bin/env python3
"""Compare each tool's diagnostics with tsc 7's for every case. It reports and does not fail:
the tools pin different TypeScript versions. Writes results/diagnostics.md.
usage: scripts/bench-apps/verify.py <work-dir> [--case CASE]"""
import argparse
import re
from pathlib import Path

CASES = ['vscode', 'sentry', 'playwright', 'typeorm', 'excalidraw', 'trpc-server'] + [
    f't3-{p}-noeffect' for p in ['apps-server', 'apps-web', 'apps-mobile', 'packages-client-runtime', 'packages-shared']]
TOOLS = ['tsc-rs', 'tsc-rs-fast', 'tsc-ts', 'tsrs', 'bun']


def records(text: str) -> list[tuple[str, ...]]:
    """Keep each diagnostic header with its complete indented message chain."""
    diagnostics, current = [], None
    for line in text.splitlines():
        if re.search(r'(?:error|warning|message|suggestion) TS-?\d+:', line):
            current = [line]
            diagnostics.append(current)
        elif current is not None and line.startswith((' ', '\t')):
            current.append(line)
        else:
            current = None
    return sorted(tuple(d) for d in diagnostics)


def cell(results: Path, case: str, tool: str, go: list | None) -> str:
    """'MATCH n', 'DIFF n (-missing +extra)', 'failed' or '-' (not run)."""
    errors = results / f'{case}.errors'
    status = {r.split()[0]: r for r in errors.read_text().splitlines()} if errors.exists() else {}
    if tool not in status:
        return '-'
    if status[tool].endswith('failed'):
        return status[tool].split(maxsplit=1)[1]
    found = sorted(r for s in ['stdout', 'stderr'] for r in records((results / f'{case}.{tool}.{s}').read_text()))
    if go is None or found == go:
        return f'MATCH {len(found)}'
    missing, extra = len(set(go) - set(found)), len(set(found) - set(go))
    return f'DIFF {len(found)} (-{missing} +{extra})'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work', type=Path)
    parser.add_argument('--case', choices=CASES)
    args = parser.parse_args()
    results = args.work / 'results'
    rows = ['| Case | tsc7 | ' + ' | '.join(TOOLS) + ' |', '| --- |' + ' --- |' * (len(TOOLS) + 1)]
    for case in [args.case] if args.case else CASES:
        if not (results / f'{case}.errors').exists():
            continue
        go_file = results / f'{case}.tsc7.stdout'
        go = sorted(r for s in ['stdout', 'stderr'] for r in records((results / f'{case}.tsc7.{s}').read_text())) \
            if go_file.exists() else None
        rows.append(f'| {case} | {len(go) if go is not None else "-"} | '
                    + ' | '.join(cell(results, case, t, go) for t in TOOLS) + ' |')
    table = '\n'.join(rows) + '\n'
    print(table)
    if not args.case:
        (results / 'diagnostics.md').write_text(table)
