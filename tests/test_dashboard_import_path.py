import subprocess
import sys
from pathlib import Path


def test_dashboard_imports_work_from_dashboard_directory():
    project_root = Path(__file__).resolve().parents[1]
    dashboard_dir = project_root / "dashboard"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from path_bootstrap import ensure_project_root_on_path; "
                "ensure_project_root_on_path('app.py'); "
                "import dashboard.queries; "
                "import dashboard.charts; "
                "print('ok')"
            ),
        ],
        cwd=dashboard_dir,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
