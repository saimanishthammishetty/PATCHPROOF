"""Root conftest: ensure the repo root is on sys.path so `scripts.*` is importable."""
import sys
import os

# Add the project root (C:\PATCHPROOF) to sys.path so that `scripts` package is importable
sys.path.insert(0, os.path.dirname(__file__))

