## Problem

Describe the integrity or usability problem.

## Solution

Explain the change, manifest compatibility, and safety decisions.

## Validation

- [ ] `python -m py_compile integrity_checker.py`
- [ ] `python -m unittest discover -v`
- [ ] `python examples/run_demo.py`
- [ ] Documentation and changelog updated when needed
- [ ] Fixtures contain no private paths, hashes, credentials, or personal files
