from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAYWRIGHT_BROWSERS_DIR = PROJECT_ROOT / ".playwright-browsers"
BROWSER_ARCHIVE = PROJECT_ROOT / ".playwright-browsers.zip"
SPEC_PATH = PROJECT_ROOT / "packaging" / "bi_validator.spec"


def run(command: list[str], env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, env=env, check=True)


def ensure_playwright_browser(browser: str) -> None:
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(PLAYWRIGHT_BROWSERS_DIR)
    run([sys.executable, "-m", "playwright", "install", browser], env=env)


def prepare_playwright_archive() -> None:
    if not PLAYWRIGHT_BROWSERS_DIR.exists():
        raise FileNotFoundError(f"Playwright browser cache not found: {PLAYWRIGHT_BROWSERS_DIR}")
    if BROWSER_ARCHIVE.exists() and BROWSER_ARCHIVE.stat().st_mtime >= PLAYWRIGHT_BROWSERS_DIR.stat().st_mtime:
        return
    if BROWSER_ARCHIVE.exists():
        BROWSER_ARCHIVE.unlink()
    shutil.make_archive(
        base_name=str(BROWSER_ARCHIVE.with_suffix("")),
        format="zip",
        root_dir=PROJECT_ROOT,
        base_dir=PLAYWRIGHT_BROWSERS_DIR.name,
    )


def build(clean: bool) -> None:
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm"]
    if clean:
        command.append("--clean")
    command.append(str(SPEC_PATH))
    run(command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a one-file BI Dashboard Validator executable with PyInstaller.")
    parser.add_argument(
        "--browser",
        default="chromium",
        help="Playwright browser to bundle into the executable. Chromium is the supported default.",
    )
    parser.add_argument(
        "--skip-browser-install",
        action="store_true",
        help="Skip Playwright browser installation and reuse the existing .playwright-browsers cache.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Reuse the previous PyInstaller work directory instead of cleaning it first.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.skip_browser_install or not PLAYWRIGHT_BROWSERS_DIR.exists():
        ensure_playwright_browser(args.browser)
    prepare_playwright_archive()
    build(clean=not args.no_clean)


if __name__ == "__main__":
    main()
