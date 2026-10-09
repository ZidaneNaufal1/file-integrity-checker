# File Integrity Checker

[![Tests](https://github.com/ZidaneNaufal1/file-integrity-checker/actions/workflows/tests.yml/badge.svg)](https://github.com/ZidaneNaufal1/file-integrity-checker/actions/workflows/tests.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A dependency-free Python CLI that records SHA-256 fingerprints for a directory
and reports files that were changed, added, removed, or could not be read.

## Why This Exists

Backups and transferred folders can look complete while containing silent
changes. This tool creates a portable JSON manifest so users can verify data
without modifying the source directory.

## Features

- SHA-256 hashing in bounded memory
- Recursive scanning with stable relative paths
- Detection of changed, missing, and added files
- Explicit reporting of unreadable files
- Atomic JSON writes to avoid partial manifests
- Symbolic links skipped to avoid escaping the selected directory
- Human-readable and JSON verification output
- Meaningful exit codes for scripts and CI

## Requirements

- Python 3.9 or newer
- No third-party packages

## Quick Start

```bash
git clone https://github.com/ZidaneNaufal1/file-integrity-checker.git
cd file-integrity-checker
python integrity_checker.py create ./important-folder --manifest backup-manifest.json
python integrity_checker.py check ./important-folder --manifest backup-manifest.json
```

Write a machine-readable verification report:

```bash
python integrity_checker.py check ./important-folder \
  --manifest backup-manifest.json \
  --report integrity-report.json \
  --json
```

## Reproducible Demo

```bash
python examples/run_demo.py
```

The demonstration creates disposable files, records a manifest, verifies the
clean state, then makes controlled changes and proves that changed, missing,
and added files are identified. It runs against a temporary directory and is
also executed by GitHub Actions.

## Exit Codes

| Code | Meaning |
|---:|---|
| `0` | Manifest created or verification is clean |
| `1` | Verification found changes or unreadable files |
| `2` | Invalid input, manifest, or output error |

## Safety and Limitations

The tool reads files and writes only the selected manifest or report. It does
not repair, delete, move, or restore files. A SHA-256 match confirms content
equality with the recorded manifest; it does not prove that the original file
was trustworthy. Metadata such as permissions and timestamps is not tracked.

## Tests

```bash
python -m unittest discover -v
```

The suite covers clean verification, changes, missing and new files, paths with
spaces, corrupt manifests, manifest exclusion, unreadable files, and CLI exit
codes. GitHub Actions runs the suite on Python 3.9, 3.11, and 3.13.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the test
and pull request workflow. Release history is maintained in
[CHANGELOG.md](CHANGELOG.md).

## License

MIT License. See [LICENSE](LICENSE).
