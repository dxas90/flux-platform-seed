#!/usr/bin/env python3
"""Fail when tracked text files lack a final LF or contain trailing whitespace."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
files = subprocess.run(
    ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True
).stdout.split(b"\0")
errors = []
for raw in filter(None, files):
    path = root / raw.decode()
    if not path.is_file():
        continue
    data = path.read_bytes()
    if b"\0" in data:
        continue
    if data and not data.endswith(b"\n"):
        errors.append(f"{path.relative_to(root)}: missing final newline")
    for number, line in enumerate(data.splitlines(), 1):
        if line.rstrip(b" \t") != line:
            errors.append(f"{path.relative_to(root)}:{number}: trailing whitespace")
if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
print(f"PASS text hygiene for {len(files) - 1} tracked paths")
