from pathlib import Path
import sys


def ensure_project_root_on_path(file_path: str) -> None:
    """Make repo-root package imports work when Streamlit runs dashboard/app.py."""
    project_root = Path(file_path).resolve().parents[1]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
