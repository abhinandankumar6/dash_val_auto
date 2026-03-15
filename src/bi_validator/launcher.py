from __future__ import annotations

import argparse
import os
import shutil
import stat
import threading
import webbrowser
from pathlib import Path

import uvicorn

from bi_validator.core.runtime import app_data_root, bundle_root, bundled_playwright_browsers_path
from bi_validator.core.utils import ensure_directory


def _fix_playwright_permissions(root: Path) -> None:
    if os.name == "nt" or not root.exists():
        return

    executable_names = {
        "chrome",
        "Chromium",
        "chrome_crashpad_handler",
        "chrome_sandbox",
        "crashpad_handler",
        "ffmpeg",
        "firefox",
        "headless_shell",
        "minidump_upload",
        "pw_run.sh",
    }
    executable_parents = {"MacOS", "chrome-linux", "chrome-mac", "firefox", "firefox-bin"}

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in executable_names or path.suffix == ".sh" or path.parent.name in executable_parents:
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _prepare_playwright_browsers(data_dir: Path) -> Path | None:
    extracted_bundle = data_dir / ".playwright-browsers"
    if extracted_bundle.exists():
        _fix_playwright_permissions(extracted_bundle)
        return extracted_bundle

    browser_archive = bundle_root() / ".playwright-browsers.zip"
    if browser_archive.exists():
        shutil.unpack_archive(str(browser_archive), str(data_dir))
        if extracted_bundle.exists():
            _fix_playwright_permissions(extracted_bundle)
            return extracted_bundle

    bundled_path = bundled_playwright_browsers_path()
    if bundled_path:
        _fix_playwright_permissions(bundled_path)
    return bundled_path


def configure_standalone_environment(data_dir: Path, show_automation_browser: bool) -> None:
    ensure_directory(data_dir)
    ensure_directory(data_dir / "reports")
    ensure_directory(data_dir / "screenshots")

    os.environ.setdefault("APP_ENV", "standalone")
    os.environ.setdefault("AUTO_CREATE_TABLES", "true")
    os.environ.setdefault("QUEUE_BACKEND", "inline")
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{(data_dir / 'bi_validator.db').resolve().as_posix()}")
    os.environ.setdefault("REPORT_ROOT", str((data_dir / "reports").resolve()))
    os.environ.setdefault("SCREENSHOT_ROOT", str((data_dir / "screenshots").resolve()))
    os.environ.setdefault("PLAYWRIGHT_HEADLESS", "false" if show_automation_browser else "true")

    bundled_browsers = _prepare_playwright_browsers(data_dir)
    if bundled_browsers and "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled_browsers)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the BI Dashboard Validator as a self-contained local app.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface for the local web server.")
    parser.add_argument("--port", type=int, default=8000, help="Port for the local web server.")
    parser.add_argument(
        "--data-dir",
        default=str(app_data_root()),
        help="Directory for the local SQLite database, reports, and screenshots.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the app UI in the system browser.",
    )
    parser.add_argument(
        "--show-automation-browser",
        action="store_true",
        help="Show the dashboard automation browser instead of running it headless.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir).expanduser().resolve()
    configure_standalone_environment(data_dir, show_automation_browser=args.show_automation_browser)

    launch_url = f"http://{args.host}:{args.port}/"
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(launch_url)).start()

    print("BI Dashboard Validator")
    print(f"UI: {launch_url}")
    print(f"Data directory: {data_dir}")
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        print(f"Bundled Playwright browsers: {os.environ['PLAYWRIGHT_BROWSERS_PATH']}")
    else:
        print("Bundled Playwright browsers: not configured; Playwright will use its default lookup path.")

    from bi_validator.main import app

    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
