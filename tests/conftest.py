"""Make the project folder importable in tests (e.g. `from utils.text import ...`)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
