"""Pytest bootstrap — make the backend package root importable so tests can
`from services.orchestrator import ...` regardless of the working directory."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
