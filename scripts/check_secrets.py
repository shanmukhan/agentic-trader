"""Small project-specific working-tree check. Complements, not replaces, secret scanning."""

import re
import subprocess
import sys
from pathlib import Path

result = subprocess.run(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
    check=True,
    capture_output=True,
    text=True,
)
bad = []
pattern = re.compile(
    r"(?m)^[ \t]*(?:export[ \t]+)?(?:KITE_API_KEY|KITE_API_SECRET|KITE_ACCESS_TOKEN|"
    r"TRADING_OPERATOR_TOKEN)[ \t]*=[ \t]*[\"']?[A-Za-z0-9_-]{16,}"
)
for name in result.stdout.splitlines():
    path = Path(name)
    if path.is_file() and path.suffix not in (".lock",):
        content = path.read_text(errors="replace")
        if pattern.search(content) or ("-----BEGIN " + "PRIVATE KEY-----") in content:
            bad.append(name)
if bad:
    print("Potential secret material in: " + ", ".join(bad), file=sys.stderr)
    sys.exit(1)
print("Project-specific secret patterns: clean")
