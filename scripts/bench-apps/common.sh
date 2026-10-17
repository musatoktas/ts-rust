#!/usr/bin/env bash
# Shared paths and measurement checks for run.sh and t3code.sh.
# The callers use the tool paths and supply names and sel.
# shellcheck disable=SC2034,SC2154
bench_tools() {
  local nm=$1/node_modules
  [[ "$(uname -s)/$(uname -m)" == Linux/x86_64 ]] || { echo "unsupported benchmark platform" >&2; exit 1; }
  GO=$nm/@typescript/typescript-linux-x64/lib/tsc
  RS=$nm/@tsc-rs/linux-x64/lib/tsc
  TSCTS=$nm/@tsc-ts/linux-x64-gnu/lib/tsc-ts
  TSRS=$nm/@tsrs/linux-x64-gnu/tsrs
  # bun's postinstall moves the native binary here from @oven/bun-linux-x64.
  BUN=$nm/bun/bin/bun.exe
  local b
  for b in "$GO" "$RS" "$TSCTS" "$TSRS" "$BUN"; do [[ -x $b ]] || { echo "missing tool: $b" >&2; exit 1; }; done
}

# Keep every preflight's full output. A tool that crashes or runs over 10 minutes in its
# preflight is not timed ("failed" in .errors). Every timed run must have the same exit code
# as its preflight; diagnostic exits (1 or 2) are valid.
bench_measure() {
  local out=$1; shift
  local cmds=("$@") args=() i rc
  [[ ! -e $out.json ]] || { echo "result already exists: $out.json" >&2; exit 1; }
  : >"$out.errors"
  for i in "${sel[@]}"; do
    rc=0
    timeout 600 bash -c "${cmds[$i]}" >"$out.${names[$i]}.stdout" 2>"$out.${names[$i]}.stderr" || rc=$?
    if ((rc > 2)); then
      echo "${names[$i]} rc=$rc failed" >>"$out.errors"
      continue
    fi
    cat "$out.${names[$i]}.stdout" "$out.${names[$i]}.stderr" |
      LC_ALL=C grep -E '(error|warning|message|suggestion) (TS-?[0-9]+|effect\()' |
      LC_ALL=C sort >"$out.${names[$i]}.diag" || true
    echo "${names[$i]} rc=$rc errors=$(wc -l <"$out.${names[$i]}.diag" | tr -d ' ')" >>"$out.errors"
    args+=(-n "${names[$i]}" "${cmds[$i]}")
  done
  echo "$(basename "$out"): $(tr '\n' ' ' <"$out.errors")"
  hyperfine -N -i --warmup 1 --runs "${RUNS:-5}" --export-json "$out.json" "${args[@]}"
  python3 - "$out" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
codes = {row.split()[0]: int(row.split()[1].split('=')[1])
         for row in Path(str(out) + '.errors').read_text().splitlines() if not row.endswith('failed')}
for run in json.loads(Path(str(out) + '.json').read_text())['results']:
    if not all(code == codes[run['command']] for code in run['exit_codes']):
        raise SystemExit(f"inconsistent exits: {run['command']}: {run['exit_codes']}")
PY
}
