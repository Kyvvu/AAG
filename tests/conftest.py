# SPDX-License-Identifier: Apache-2.0
"""Shared test setup.

The AAG repo is a specification, not a package: ``spec/generate.py`` and
``validator/validate.py`` are scripts, so make their directories importable as
top-level modules (``generate``, ``validate``) for the tests.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("spec", "validator"):
    _path = str(_ROOT / _sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)
