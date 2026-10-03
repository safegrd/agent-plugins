#!/usr/bin/env python3
"""Check that every SafeGrd MCP tool a skill names is one the remote server serves.

The skills tell an agent to call tools by name. The server publishes its tools,
without a token, in its server card. A skill that names a tool the server no
longer has fails here instead of in a customer's session.
"""
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

CARD = "https://safegrd.dev/.well-known/mcp/server-card.json"
# Tool names are verb_noun; response fields such as last_backup_at are not.
TOOL = re.compile(r"`((?:list|get|request)_[a-z_]+|drill_stats|storage_usage)`")

root = pathlib.Path(__file__).resolve().parent.parent
named = {}
for skill in sorted(root.glob("plugins/*/skills/*/SKILL.md")):
    for name in TOOL.findall(skill.read_text()):
        named.setdefault(name, []).append(str(skill.relative_to(root)))

try:
    with urllib.request.urlopen(CARD, timeout=20) as resp:
        card = json.load(resp)
except urllib.error.HTTPError as e:
    if e.code == 404:
        print(f"::warning::{CARD} answers 404, so the tool names were not checked")
        sys.exit(0)
    raise

served = {t["name"] for t in card.get("tools", [])}
missing = {n: files for n, files in named.items() if n not in served}
for name, files in sorted(missing.items()):
    print(f"::error::{name} is named in {', '.join(sorted(set(files)))} but the server does not serve it")
print(f"Checked {len(named)} tool names against {len(served)} served tools.")
sys.exit(1 if missing else 0)
