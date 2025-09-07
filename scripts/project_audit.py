#!/usr/bin/env python3
import argparse, csv, hashlib, json, os, sys, time
from pathlib import Path
from datetime import datetime

try:
    import yaml  # pip install pyyaml
except Exception as e:
    print("ERROR: pyyaml not installed. Add it to scripts/requirements.audit.txt or pip install pyyaml.", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
BP_DIR = ROOT / "blueprint"
REPORTS = ROOT / "reports"
CFG = ROOT / "project_audit.toml"

EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".idea", ".vscode", "reports", ".pytest_cache"}
EXCLUDE_FILES = set()

def sha256_file(p: Path, limit_mb=20):
    try:
        if p.is_file():
            h=hashlib.sha256()
            with open(p, "rb") as f:
                while True:
                    chunk = f.read(1024*1024)
                    if not chunk: break
                    h.update(chunk)
            return h.hexdigest()
    except Exception:
        return None

def walk_files():
    out=[]
    for dp, dn, fn in os.walk(ROOT):
        dname = Path(dp).relative_to(ROOT)
        parts = dname.parts
        if any(part in EXCLUDE_DIRS for part in parts):
            continue
        for n in fn:
            if n in EXCLUDE_FILES: 
                continue
            p = Path(dp)/n
            rel = p.relative_to(ROOT).as_posix()
            try:
                size = p.stat().st_size
            except Exception:
                size = None
            try:
                with open(p, "rb") as f:
                    head = f.read(4096)
                lines = None
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as tf:
                        lines = sum(1 for _ in tf)
                except Exception:
                    pass
            except Exception:
                head = b""
                lines = None
            out.append({
                "path": rel,
                "size": size,
                "lines": lines,
                "sha256": sha256_file(p),
                "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat() if p.exists() else None,
            })
    return sorted(out, key=lambda x: x["path"])

def read_yaml(p: Path):
    if not p.exists(): return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def ensure_reports():
    REPORTS.mkdir(parents=True, exist_ok=True)

def write_json(p: Path, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def write_text(p: Path, text: str):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

def render_tree(inv):
    lines=[]
    for item in inv:
        lines.append(item["path"])
    return "\n".join(lines)

def drift_check(manifest):
    missing=[]
    present=[]
    forbidden_hits=[]
    # required files
    required = (manifest.get("files",{}) or {}).get("required",[]) or []
    for rel in required:
        if not (ROOT/rel).exists():
            missing.append(rel)
    # forbidden globs
    from glob import glob
    fglobs = (manifest.get("files",{}) or {}).get("forbidden_globs",[]) or []
    for g in fglobs:
        for hit in glob(str(ROOT / g), recursive=True):
            hit_rel = Path(hit).resolve().relative_to(ROOT).as_posix()
            forbidden_hits.append(hit_rel)
    return missing, sorted(set(forbidden_hits))

def lock_blueprint():
    m = (BP_DIR/"manifest.yml").read_bytes() if (BP_DIR/"manifest.yml").exists() else b""
    r = (BP_DIR/"rules.yml").read_bytes() if (BP_DIR/"rules.yml").exists() else b""
    h = hashlib.sha256(m+r).hexdigest()
    write_text(ROOT/"blueprint.lock", h+"\n")

def build_todos():
    csvp = BP_DIR/"workplan.csv"
    if not csvp.exists():
        write_text(REPORTS/"todos.md", "# Todos\n\n(none)\n")
        return
    rows=[]
    with open(csvp, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    lines = ["# Todos\n"]
    for r in rows:
        lines.append(f"- [{ 'x' if (r.get('status') or '').lower()=='done' else ' '}] {r.get('id')} — {r.get('title')} ({r.get('status')})  due {r.get('due')}")
    write_text(REPORTS/"todos.md", "\n".join(lines)+"\n")

def cmd_init_from_tree():
    BP_DIR.mkdir(parents=True, exist_ok=True)
    inv = walk_files()
    default_required = []
    for candidate in ["infra/docker-compose.yml", ".env.example", "README.md", "scripts/project_audit.py", "docs/ARCHITECTURE.md"]:
        if (ROOT/candidate).exists():
            default_required.append(candidate)
    manifest = {
        "version": 1,
        "project": ROOT.name,
        "files": {
            "required": sorted(default_required),
            "forbidden_globs": ["**/*.pem", "**/.env", "**/*secret*"]
        },
        "modules": [],
        "boundaries": {"disallow_imports": []},
        "shared_code_root": "libs/",
        "artifacts": {"reports": ["reports/tree.txt","reports/inventory.json","reports/todos.md","reports/drift.md"]},
    }
    with open(BP_DIR/"manifest.yml","w",encoding="utf-8",newline="\n") as f:
        yaml.safe_dump(manifest, f, sort_keys=False)
    if not (BP_DIR/"rules.yml").exists():
        with open(BP_DIR/"rules.yml","w",encoding="utf-8",newline="\n") as f:
            yaml.safe_dump({
                "checks":{
                    "tree":{"allowed_paths":["infra/*","blueprint/*","scripts/*","docs/*","reports/*","services/*","libs/*"]},
                    "health":{"require_endpoints": True},
                    "logging":{"required_stack":"loki","files":["infra/promtail/config.yml","infra/loki/config.yml"]},
                    "ci":{"require_job":"blueprint-guard"},
                    "security":{"secret_scan": True}
                },
                "policy":{"fail_on_drift": True, "enforce_in_precommit": True, "enforce_in_ci": True}
            }, f, sort_keys=False)
    print("Initialized blueprint/manifest.yml and rules.yml from current tree.")

def cmd_strict():
    ensure_reports()
    inv = walk_files()
    write_text(REPORTS/"tree.txt", render_tree(inv))
    write_json(REPORTS/"inventory.json", inv)
    build_todos()

    manifest = read_yaml(BP_DIR/"manifest.yml")
    missing, forbidden = drift_check(manifest)

    drift_lines=["# Drift Report"]
    if missing:
        drift_lines.append("## Missing required files")
        for m in missing: drift_lines.append(f"- {m}")
    if forbidden:
        drift_lines.append("## Forbidden files present")
        for f in forbidden: drift_lines.append(f"- {f}")
    if not missing and not forbidden:
        drift_lines.append("No drift detected.")
        write_text(REPORTS/"drift.md","\n".join(drift_lines)+"\n")
        lock_blueprint()
        print("OK: no drift.")
        return 0
    else:
        write_text(REPORTS/"drift.md","\n".join(drift_lines)+"\n")
        print("DRIFT detected. See reports/drift.md", file=sys.stderr)
        lock_blueprint()
        return 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init-from-tree", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    if args.init_from_tree:
        cmd_init_from_tree()
        return 0
    if args.strict:
        return cmd_strict()
    ap.print_help()
    return 0

if __name__ == "__main__":
    sys.exit(main())
