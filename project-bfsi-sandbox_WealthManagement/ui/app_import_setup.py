"""Import setup for Streamlit scripts launched from the ``ui`` directory."""

import sys
from pathlib import Path


def configure_project_imports() -> None:
    """Make top-level Chronos packages available to ``streamlit run ui/app_navigation.py``."""
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
