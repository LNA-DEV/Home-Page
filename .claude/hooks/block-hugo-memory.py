#!/usr/bin/env python3
"""PreToolUse hook: never let Claude render this site into RAM.

The site (~7.8 GB of gallery output, ~5,500 processed images) does not fit in
memory. `hugo --renderToMemory` and a plain `hugo server` (which renders to
memory by default) have crashed every machine they ran on. Exit code 2 blocks
the Bash call and hands the message on stderr back to Claude.
"""
import json
import re
import sys

try:
    cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
except Exception:
    sys.exit(0)

flat = cmd.lower().replace("-", "").replace("_", "")

reason = None
if "rendertomemory" in flat:
    reason = "`--renderToMemory`"
elif re.search(r"(?:^|[;&|(`]|\b(?:then|do|exec|env|sudo|nohup|time)\b)\s*(?:\S+=\S*\s+)*(?:\S*/)?hugo\s[^|;&\n]*\bserver?\b", cmd) and "rendertodisk" not in flat:
    reason = "`hugo server` without `--renderToDisk` (it renders to memory by default)"

if reason:
    print(
        f"BLOCKED: {reason}. This site is far too large to render into RAM; it "
        "crashes the machine. Never retry this in any form. Build to disk instead: "
        "`hugo -d <scratch dir>` or `npm test` (builds into .test-site/). If a dev "
        "server is really needed, ask the user to run "
        "`hugo server -D --renderToDisk` themselves.",
        file=sys.stderr,
    )
    sys.exit(2)
