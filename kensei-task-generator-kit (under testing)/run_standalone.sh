#!/usr/bin/env bash
#
# run_standalone.sh
#
# Stage 2 of the Kensei task generator pipeline. Given a task folder that
# already has prompt.txt, task.yaml, GTFA.txt, home/, mock_data/, persona/,
# this script invokes STANDALONE_COMBINED_SYSTEM_PROMPT.md via opencode and
# drops rubric.json + test_output.py + test_weights.json at the task root.
#
# Usage:
#   ./run_standalone.sh "<task_folder_path>"
#
# Example:
#   ./run_standalone.sh "/Users/macbookpro/.../unified-personas/ben-cox/ben_cox 5e9c2d8b-3a7f-4e1c-8b4d-1f6a9c5e3b2d"
#
# Requirements:
#   - opencode on PATH (or set OPENCODE_BIN)
#   - python3 with pyyaml
#   - The task folder lives anywhere; this script reads its task.yaml to
#     extract required_apis and distractor_apis.
#

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 \"<task_folder_path>\"" >&2
  exit 2
fi

TASK_DIR="$1"
if [[ ! -d "$TASK_DIR" ]]; then
  echo "error: not a directory: $TASK_DIR" >&2
  exit 2
fi

KIT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYS_PROMPT="$KIT_DIR/reference/STANDALONE_COMBINED_SYSTEM_PROMPT.md"
ENV_DIR="$KIT_DIR/environment"
OPENCODE_BIN="${OPENCODE_BIN:-opencode}"

if [[ ! -f "$SYS_PROMPT" ]]; then
  echo "error: missing $SYS_PROMPT" >&2
  exit 1
fi
if [[ ! -d "$ENV_DIR" ]]; then
  echo "error: missing $ENV_DIR" >&2
  exit 1
fi
if [[ ! -x "$(command -v "$OPENCODE_BIN")" ]]; then
  echo "error: opencode not on PATH; set OPENCODE_BIN or install opencode" >&2
  exit 1
fi

REQUIRED=$(python3 -c "
import sys, yaml
d = yaml.safe_load(open('$TASK_DIR/task.yaml'))
print(', '.join(d.get('required_apis', [])))
")
DISTRACTOR=$(python3 -c "
import sys, yaml
d = yaml.safe_load(open('$TASK_DIR/task.yaml'))
print(', '.join(d.get('distractor_apis', [])))
")

echo "task: $TASK_DIR"
echo "required_apis: $REQUIRED"
echo "distractor_apis: $DISTRACTOR"

MSG=$(cat <<EOF
You are running Stage 2 of the Kensei task generator. Treat the attached file
STANDALONE_COMBINED_SYSTEM_PROMPT.md as your complete operating instructions.
Follow it exactly.

Task folder under inspection: $TASK_DIR
  - prompt.txt, task.yaml, GTFA.txt at the task root
  - home/ contains the persona macOS tree plus task overlays
  - mock_data/ contains the persona mock baseline plus task overlays
  - persona/ contains the 7 .md persona files

The canonical mock-API source-of-truth lives at $ENV_DIR (each
<api>-api/ has server.py + <name>_data.py + service.toml + *.json seeds).

Read $TASK_DIR/prompt.txt and the task content. Generate the three files
the STANDALONE prompt specifies (rubric.json, test_outputs.py, test_weights.json)
as one fenced JSON block with three string-valued keys, exactly as
STANDALONE_COMBINED_SYSTEM_PROMPT.md describes.

Required APIs for this task: ${REQUIRED}.
Distractor APIs for this task: ${DISTRACTOR}.
EOF
)

OUT_FILE=$(mktemp -t kensei-standalone.XXXXXX)
trap 'rm -f "$OUT_FILE"' EXIT

echo ""
echo "invoking opencode (this can take a minute or two)..."
"$OPENCODE_BIN" run \
  --dir "$TASK_DIR" \
  --file "$SYS_PROMPT" \
  --file "$TASK_DIR/prompt.txt" \
  --file "$TASK_DIR/task.yaml" \
  --file "$TASK_DIR/GTFA.txt" \
  -- "$MSG" > "$OUT_FILE"

rm -f "$TASK_DIR/sqlite_mcp_server.db"

python3 <<PY
import json, re, sys
from pathlib import Path

raw = Path("$OUT_FILE").read_text()
# STANDALONE outputs one fenced block. The opencode --format json wraps that
# in an event stream; grab the final assistant message text.
text = raw
# Try to extract a single fenced json block.
m = re.search(r"\`\`\`(?:json)?\s*(\{.*?\})\s*\`\`\`", text, re.DOTALL)
if not m:
    # Fall back: maybe the model emitted a bare JSON object.
    m = re.search(r"(\{[\s\S]*\})", text)
if not m:
    print("error: could not find a JSON block in the model output", file=sys.stderr)
    print(text[:4000], file=sys.stderr)
    sys.exit(3)

payload = json.loads(m.group(1))
required_keys = ["tests/rubric.json", "tests/test_outputs.py", "tests/test_weights.json"]
if not all(k in payload for k in required_keys):
    # The kit README accepts either "tests/test_outputs.py" or
    # "tests/test_output.py" since pytest collects either.
    if "tests/test_output.py" in payload and "tests/test_outputs.py" not in payload:
        payload["tests/test_outputs.py"] = payload["tests/test_output.py"]

target = Path("$TASK_DIR")
(target / "rubric.json").write_text(payload["tests/rubric.json"])
(target / "test_output.py").write_text(payload["tests/test_outputs.py"])
(target / "test_weights.json").write_text(payload["tests/test_weights.json"])
print("wrote:", target / "rubric.json")
print("wrote:", target / "test_output.py")
print("wrote:", target / "test_weights.json")
PY

echo ""
echo "done."
