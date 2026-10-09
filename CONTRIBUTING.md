# Contributing

Thank you for improving File Integrity Checker.

1. Open an issue for a bug or substantial feature.
2. Create a focused branch from `main`.
3. Preserve the read-only behavior for scanned directories.
4. Add tests for changed behavior.
5. Run `python -m py_compile integrity_checker.py` and
   `python -m unittest discover -v`.
6. Update the README or changelog when users will notice the change.
7. Open a pull request explaining the problem, solution, and test evidence.

Tests must use temporary directories and must never scan or modify personal
folders. Do not add dependencies without documenting the reason and tradeoff.
