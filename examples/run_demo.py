#!/usr/bin/env python3
"""Run a reproducible integrity-check demonstration in a temporary folder."""

import json
from pathlib import Path
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from integrity_checker import build_manifest, verify_manifest, write_json_atomic  # noqa: E402


def main():
    with tempfile.TemporaryDirectory(prefix="integrity-demo-") as temporary:
        workspace = Path(temporary)
        data = workspace / "archive"
        data.mkdir()
        (data / "report.txt").write_text("original report", encoding="utf-8")
        (data / "photo.bin").write_bytes(b"original photo")
        manifest_path = workspace / "manifest.json"

        manifest = build_manifest(data, manifest_path)
        write_json_atomic(manifest_path, manifest)
        clean = verify_manifest(data, manifest_path)
        print("INITIAL CHECK")
        print(json.dumps(clean, indent=2, sort_keys=True))
        assert clean["clean"]

        (data / "report.txt").write_text("edited report", encoding="utf-8")
        (data / "photo.bin").unlink()
        (data / "new-note.txt").write_text("new file", encoding="utf-8")

        changed = verify_manifest(data, manifest_path)
        print("\nAFTER CONTROLLED CHANGES")
        print(json.dumps(changed, indent=2, sort_keys=True))
        assert changed["changed"] == ["report.txt"]
        assert changed["missing"] == ["photo.bin"]
        assert changed["added"] == ["new-note.txt"]

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
