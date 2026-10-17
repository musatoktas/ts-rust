#!/usr/bin/env python3
"""Prints the median time of each tool per case and its speed against tsc 7, the geometric mean
speedup over the apps, and the T3 Code sum of the five projects. A tool that failed a case has no
time there and is left out of that sum and mean.
usage: scripts/bench-apps/summary.py <work-dir>"""
import json, math, sys
from pathlib import Path

R = Path(sys.argv[1]) / 'results'
APPS = ['vscode', 'sentry', 'playwright', 'typeorm', 'excalidraw', 'trpc-server']
T3 = [f't3-{p}-noeffect' for p in ['apps-server', 'apps-web', 'apps-mobile', 'packages-client-runtime', 'packages-shared']]
TOOLS = ['tsc7', 'tsc-rs', 'tsc-rs-fast', 'tsc-ts', 'tsrs', 'bun']


def medians(stem: str) -> dict[str, float] | None:
    """Median time per tool for one result stem: the full run, then each limited run over it."""
    if not (R / f'{stem}.json').exists():
        return None
    med = {}
    for f in [R / f'{stem}.json', *sorted(R.glob(f'{stem}.*.json'))]:
        med |= {r['command']: r['median'] for r in json.load(open(f))['results']}
    return med


def table(cases: list[str]) -> None:
    print('| Case | ' + ' | '.join(TOOLS) + ' |\n| --- |' + ' ---: |' * len(TOOLS))
    vs7 = {t: [] for t in TOOLS}
    for case in cases:
        if (med := medians(case)) is None:
            continue
        cells = []
        for t in TOOLS:
            if t not in med:
                cells.append('failed')
                continue
            cells.append(f'{med[t]:.2f}s' + ('' if t == 'tsc7' else f' ({med["tsc7"] / med[t]:.2f}×)'))
            vs7[t].append(med['tsc7'] / med[t])
        print(f'| {case} | ' + ' | '.join(cells) + ' |')
    print()
    for t in TOOLS[1:]:
        if vs7[t]:
            print(f'- {t}: {math.exp(sum(map(math.log, vs7[t])) / len(vs7[t])):.2f}× tsc7 '
                  f'(geometric mean of {len(vs7[t])})')
    print()


print('## Apps\n')
table(APPS)
print('## T3 Code (no Effect)\n')
table(T3)
meds = [m for m in map(medians, T3) if m]
if len(meds) == len(T3):
    print(f'Sum of {len(T3)} projects (tools that ran all {len(T3)}):\n')
    total = {t: sum(m[t] for m in meds) for t in TOOLS if all(t in m for m in meds)}
    for t in sorted(total, key=total.get):
        print(f'- {t}: {total[t]:.2f}s, {total["tsc7"] / total[t]:.2f}× tsc7')
diag = R / 'diagnostics.md'
if diag.exists():
    print('\n## Diagnostics against tsc 7.0.2\n\n' + diag.read_text())
