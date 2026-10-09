#!/usr/bin/env python3
"""Create and verify SHA-256 manifests for directory trees."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


MANIFEST_VERSION = 1
CHUNK_SIZE = 1024 * 1024


class IntegrityError(Exception):
    """Raised for expected input and manifest errors."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def scan_directory(root: Path, excluded: Iterable[Path] = ()) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, str]]]:
    """Return file metadata and non-fatal read errors for *root*."""
    root = root.resolve()
    excluded_paths = {path.resolve() for path in excluded}
    files: Dict[str, Dict[str, Any]] = {}
    errors: List[Dict[str, str]] = []

    for current_root, directory_names, file_names in os.walk(root, followlinks=False):
        current = Path(current_root)
        directory_names[:] = sorted(
            name for name in directory_names if not (current / name).is_symlink()
        )
        for name in sorted(file_names):
            path = current / name
            if path.resolve() in excluded_paths or path.is_symlink():
                continue
            relative = _display_path(path, root)
            try:
                stat = path.stat()
                files[relative] = {
                    "sha256": sha256_file(path),
                    "size": stat.st_size,
                }
            except OSError as exc:
                errors.append({"path": relative, "error": str(exc)})

    return files, errors


def build_manifest(root: Path, manifest_path: Optional[Path] = None) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise IntegrityError(f"Directory does not exist: {root}")

    excluded = [manifest_path] if manifest_path else []
    files, errors = scan_directory(root, excluded)
    if errors:
        details = "; ".join(f"{item['path']}: {item['error']}" for item in errors)
        raise IntegrityError(f"Unable to read every file: {details}")

    return {
        "version": MANIFEST_VERSION,
        "algorithm": "sha256",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "files": files,
    }


def write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=str(path.parent), delete=False
        ) as temporary:
            temporary_name = temporary.name
            json.dump(data, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
        os.replace(temporary_name, path)
    except OSError as exc:
        if temporary_name:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass
        raise IntegrityError(f"Unable to write {path}: {exc}") from exc


def load_manifest(path: Path) -> Dict[str, Any]:
    try:
        with path.expanduser().open("r", encoding="utf-8") as source:
            manifest = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"Unable to read manifest {path}: {exc}") from exc

    if not isinstance(manifest, dict):
        raise IntegrityError("Manifest root must be a JSON object")
    if manifest.get("version") != MANIFEST_VERSION:
        raise IntegrityError(f"Unsupported manifest version: {manifest.get('version')!r}")
    if manifest.get("algorithm") != "sha256":
        raise IntegrityError("Manifest algorithm must be sha256")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise IntegrityError("Manifest files must be a JSON object")
    for relative, metadata in files.items():
        if not isinstance(relative, str) or not isinstance(metadata, dict):
            raise IntegrityError("Manifest contains an invalid file entry")
        digest = metadata.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise IntegrityError(f"Invalid SHA-256 value for {relative}")
    return manifest


def verify_manifest(root: Path, manifest_path: Path) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise IntegrityError(f"Directory does not exist: {root}")
    manifest = load_manifest(manifest_path)
    current, unreadable = scan_directory(root, [manifest_path])
    expected = manifest["files"]

    expected_names = set(expected)
    current_names = set(current)
    missing = sorted(expected_names - current_names)
    added = sorted(current_names - expected_names)
    changed = sorted(
        name
        for name in expected_names & current_names
        if expected[name]["sha256"] != current[name]["sha256"]
        or expected[name].get("size") != current[name].get("size")
    )
    clean = not (missing or added or changed or unreadable)
    return {
        "clean": clean,
        "summary": {
            "expected": len(expected),
            "scanned": len(current),
            "missing": len(missing),
            "added": len(added),
            "changed": len(changed),
            "unreadable": len(unreadable),
        },
        "missing": missing,
        "added": added,
        "changed": changed,
        "unreadable": unreadable,
    }


def _print_report(report: Dict[str, Any]) -> None:
    status = "CLEAN" if report["clean"] else "CHANGES DETECTED"
    print(f"Integrity status: {status}")
    for key in ("expected", "scanned", "missing", "added", "changed", "unreadable"):
        print(f"  {key.capitalize()}: {report['summary'][key]}")
    for category in ("missing", "added", "changed"):
        if report[category]:
            print(f"\n{category.capitalize()}:")
            for path in report[category]:
                print(f"  - {path}")
    if report["unreadable"]:
        print("\nUnreadable:")
        for item in report["unreadable"]:
            print(f"  - {item['path']}: {item['error']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create and verify SHA-256 manifests without modifying source files."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a manifest")
    create.add_argument("directory", type=Path)
    create.add_argument("--manifest", type=Path, default=Path("integrity-manifest.json"))

    check = subparsers.add_parser("check", help="Verify a directory")
    check.add_argument("directory", type=Path)
    check.add_argument("--manifest", type=Path, default=Path("integrity-manifest.json"))
    check.add_argument("--report", type=Path, help="Write the verification result as JSON")
    check.add_argument("--json", action="store_true", help="Print JSON instead of text")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "create":
            manifest = build_manifest(args.directory, args.manifest)
            write_json_atomic(args.manifest, manifest)
            print(f"Manifest written: {args.manifest.resolve()}")
            print(f"Files recorded: {len(manifest['files'])}")
            return 0

        report = verify_manifest(args.directory, args.manifest)
        if args.report:
            write_json_atomic(args.report, report)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            _print_report(report)
        return 0 if report["clean"] else 1
    except IntegrityError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
