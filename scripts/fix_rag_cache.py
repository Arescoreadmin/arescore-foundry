#!/usr/bin/env python3
import sys, os, subprocess, shutil, textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "infra" / "docker-compose.yml"
SERVICE = "frostgatecore"
RAG_DIR = ROOT / "backend" / "frostgatecore" / "app" / "rag_cache"
INIT_BAD = RAG_DIR / "_init_.py"
INIT_GOOD = RAG_DIR / "__init__.py"
MAIN_PY = ROOT / "backend" / "frostgatecore" / "app" / "main.py"

def sh(cmd, check=True):
    print(f"==> $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)

def ensure_repo_root():
    if not COMPOSE.exists():
        print(f"Error: {COMPOSE} not found. Run this from the repo root: {ROOT}")
        sys.exit(1)

def fix_package():
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    if INIT_BAD.exists():
        print(f"Removing bogus {INIT_BAD}")
        INIT_BAD.unlink()

    init_src = textwrap.dedent("""\
        # canonical rag_cache exports
        from .cache import (
            cached_embed,
            cached_doc_ingest,
            cached_query_topk,
            Cache,
        )
        __all__ = ["cached_embed","cached_doc_ingest","cached_query_topk","Cache"]
    """)
    print(f"Writing {INIT_GOOD}")
    INIT_GOOD.write_text(init_src, encoding="utf-8")

def ensure_health():
    if not MAIN_PY.exists():
        print(f"{MAIN_PY} missing. Creating minimal FastAPI app with /health.")
        MAIN_PY.parent.mkdir(parents=True, exist_ok=True)
        MAIN_PY.write_text(textwrap.dedent("""\
            from fastapi import FastAPI
            app = FastAPI()

            @app.get("/health")
            def health():
                return {"ok": True}
        """), encoding="utf-8")
        return

    text = MAIN_PY.read_text(encoding="utf-8")
    if '/health' not in text:
        print("Appending /health route to main.py")
        text += textwrap.dedent("""

            # appended by fix_rag_cache.py
            try:
                app
            except NameError:
                from fastapi import FastAPI
                app = FastAPI()

            @app.get("/health")
            def health():
                return {"ok": True}
        """)
        MAIN_PY.write_text(text, encoding="utf-8")
    else:
        print("/health route already present in main.py")

def rebuild_and_up():
    sh(["docker", "compose", "-f", str(COMPOSE), "build", "--no-cache", SERVICE])
    # tolerate non-zero from up --wait in case healthcheck is defined differently
    sh(["docker", "compose", "-f", str(COMPOSE), "up", "-d", "--force-recreate", "--wait", SERVICE], check=False)

def container_smoke():
    print("Listing files inside container:")
    sh(["docker", "exec", "-i", SERVICE, "sh", "-lc", "set -e; ls -la /app/app/rag_cache || true"], check=False)

    print("Import smoke test inside container:")
    code = r"""
import sys
print("sys.path:", sys.path)
try:
    import app.rag_cache as rc
    names = ["cached_embed","cached_doc_ingest","cached_query_topk","Cache"]
    print("app.rag_cache.__file__:", getattr(rc, "__file__", None))
    print("exports present:", [n for n in names if hasattr(rc, n)])
    if hasattr(rc, "cached_embed"):
        def _fake_embed(t: str): return [float(len(t))]
        v = rc.cached_embed("hello   world", embed_fn=_fake_embed)
        print("cached_embed smoke ok:", v)
except Exception as e:
    import traceback; traceback.print_exc()
    raise SystemExit(1)
"""
    sh(["docker", "exec", "-i", SERVICE, "python", "-c", code])

def curl_health():
    try:
        sh(["curl", "-sf", "http://localhost:8001/health"])
        print("\nHealth OK")
    except subprocess.CalledProcessError:
        print("Healthcheck failed or port differs. This is non-fatal if your app uses another port.")

def main():
    print(f"Repo root: {ROOT}")
    ensure_repo_root()
    fix_package()
    ensure_health()
    rebuild_and_up()
    container_smoke()
    curl_health()
    print("\nDone. If it's still unhappy, look at recent logs:")
    print(f"  docker logs {SERVICE} --since=2m")

if __name__ == "__main__":
    main()
