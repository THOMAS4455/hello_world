#!/usr/bin/env python3
"""
One-click startup for backend and frontend.
"""

import subprocess
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path


def _ensure_log_dirs(project_root: Path) -> Path:
    logs_dir = project_root / "logs"
    (logs_dir / "backend").mkdir(parents=True, exist_ok=True)
    (logs_dir / "frontend").mkdir(parents=True, exist_ok=True)
    (logs_dir / "root_archive").mkdir(parents=True, exist_ok=True)
    return logs_dir


def _archive_root_logs(project_root: Path, archive_dir: Path) -> None:
    for path in project_root.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".log", ".out", ".err"}:
            continue
        target = archive_dir / path.name
        if target.exists():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = archive_dir / f"{path.stem}_{stamp}{path.suffix}"
        path.replace(target)


def _start_backend(project_root: Path, logs_dir: Path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backend_out = (logs_dir / "backend" / f"backend_{timestamp}.out.log").open("a", encoding="utf-8")
    backend_err = (logs_dir / "backend" / f"backend_{timestamp}.err.log").open("a", encoding="utf-8")
    return subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=project_root,
        stdout=backend_out,
        stderr=backend_err,
    )


def _start_frontend(project_root: Path, logs_dir: Path):
    frontend_dir = project_root / "frontend"
    if not frontend_dir.exists():
        raise FileNotFoundError("frontend directory not found")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    frontend_out = (logs_dir / "frontend" / f"frontend_{timestamp}.out.log").open(
        "a", encoding="utf-8"
    )
    frontend_err = (logs_dir / "frontend" / f"frontend_{timestamp}.err.log").open(
        "a", encoding="utf-8"
    )

    return subprocess.Popen(
        ["npm.cmd", "start"],
        cwd=frontend_dir,
        stdout=frontend_out,
        stderr=frontend_err,
    )


def main():
    project_root = Path(__file__).resolve().parent.parent
    logs_dir = _ensure_log_dirs(project_root)
    _archive_root_logs(project_root, logs_dir / "root_archive")
    print("Starting project...")

    backend = _start_backend(project_root, logs_dir)
    time.sleep(5)
    if backend.poll() is not None:
        print("Backend failed to start.")
        return

    frontend = _start_frontend(project_root, logs_dir)
    print("Waiting for frontend (React compile may take 30-90s)...")
    for _ in range(24):
        time.sleep(5)
        if frontend.poll() is not None:
            break
        # optional: could check port 3000 here
    if frontend.poll() is not None:
        print("Frontend failed to start.")
        backend.terminate()
        return

    print("Backend: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("Frontend: http://localhost:3000")

    webbrowser.open("http://localhost:3000")
    webbrowser.open("http://localhost:8000/docs")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping services...")
        backend.terminate()
        frontend.terminate()
        print("Stopped.")


if __name__ == "__main__":
    main()
