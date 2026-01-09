#!/usr/bin/env python3
import sys
import json
import pathlib
tpl_path = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
payload = json.load(sys.stdin)
for k, v in payload.items():
    tpl_path = tpl_path.replace(f"{{{{{k}}}}}", v)
print(tpl_path)
