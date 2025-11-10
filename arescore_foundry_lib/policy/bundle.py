"""Utilities for computing and distributing OPA policy bundles."""

from __future__ import annotations

import base64
import io
import json
import os
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

__all__ = ["PolicyBundle", "discover_policy_root"]


@dataclass(frozen=True)
class PolicyBundle:
    """Representation of a policy bundle materialized from the filesystem."""

    root: Path
    files: Sequence[Path]
    packages: Sequence[str]
    version: str

    @classmethod
    def from_directory(cls, root: Path | str) -> "PolicyBundle":
        path = Path(root)
        if not path.exists():
            raise FileNotFoundError(f"Policy directory '{path}' does not exist")

        files = sorted(p for p in path.rglob("*.rego") if p.is_file())
        if not files:
            raise ValueError(f"No .rego files found under {path}")

        packages: List[str] = []
        for file_path in files:
            pkg = _extract_package_name(file_path)
            if not pkg:
                raise ValueError(f"Unable to find package declaration in {file_path}")
            packages.append(pkg)

        version = _compute_version(path, files)
        return cls(root=path, files=files, packages=packages, version=version)

    def manifest(self) -> Dict[str, object]:
        return {
            "version": self.version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "packages": list(self.packages),
            "files": [str(p.relative_to(self.root)) for p in self.files],
        }

    def to_tarball(self) -> bytes:
        """Serialize the bundle into an OPA-compatible tar.gz archive."""

        manifest_bytes = json.dumps(self.manifest(), sort_keys=True).encode("utf-8")
        manifest_io = io.BytesIO(manifest_bytes)

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for file_path in self.files:
                arcname = str(file_path.relative_to(self.root))
                tar.add(file_path, arcname=arcname)

            info = tarfile.TarInfo(name="manifest.json")
            info.size = len(manifest_bytes)
            info.mtime = int(datetime.now(timezone.utc).timestamp())
            manifest_io.seek(0)
            tar.addfile(info, manifest_io)

        buf.seek(0)
        return buf.read()

    def to_base64(self) -> str:
        return base64.b64encode(self.to_tarball()).decode("ascii")

    def write_tarball(self, destination: Path | str) -> Path:
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_tarball()
        destination_path.write_bytes(data)
        return destination_path


def discover_policy_root() -> Path:
    env_override = os.getenv("POLICY_DIR")
    if env_override:
        return Path(env_override)
    return Path(__file__).resolve().parents[2] / "policies"


def _extract_package_name(path: Path) -> str:
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("package "):
            return stripped.split(" ", 1)[1]
    return ""


def _compute_version(root: Path, files: Iterable[Path]) -> str:
    digest = sha256()
    digest.update(str(root.resolve()).encode("utf-8"))
    for file_path in files:
        digest.update(str(file_path.relative_to(root)).encode("utf-8"))
        digest.update(file_path.read_bytes())
    return digest.hexdigest()
