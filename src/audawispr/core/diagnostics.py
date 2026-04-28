"""Runtime diagnostics for local audawispr execution."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from audawispr.__about__ import __version__

FFMPEG_ENV = "AUDAWISPR_FFMPEG"
FFPROBE_ENV = "AUDAWISPR_FFPROBE"


@dataclass(frozen=True)
class ToolStatus:
    """Availability details for one external media tool."""

    name: str
    available: bool
    source: str
    path: str | None = None
    version: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class DiagnosticsReport:
    """Current local runtime readiness report."""

    package_version: str
    python_version: str
    tools: tuple[ToolStatus, ...]


def collect_diagnostics() -> DiagnosticsReport:
    """Collect local package, Python, FFmpeg, and FFprobe readiness."""
    return DiagnosticsReport(
        package_version=__version__,
        python_version=sys.version.split()[0],
        tools=(
            find_media_tool("ffmpeg", FFMPEG_ENV),
            find_media_tool("ffprobe", FFPROBE_ENV),
        ),
    )


def find_media_tool(
    name: str,
    env_var: str,
    *,
    which: Callable[[str], str | None] = shutil.which,
) -> ToolStatus:
    """Find a media binary from env vars, PATH, or static-ffmpeg."""
    explicit_path = os.environ.get(env_var)
    if explicit_path:
        return _status_for_path(name, Path(explicit_path), f"{env_var}")

    path_tool = which(name)
    if path_tool is not None:
        return _status_for_path(name, Path(path_tool), "PATH")

    static_tool, static_message = _find_static_ffmpeg_tool(name)
    if static_tool is not None:
        return _status_for_path(name, static_tool, "static-ffmpeg")

    message = "not found in environment variable, PATH, or static-ffmpeg"
    if static_message:
        message = f"{message}; static-ffmpeg: {static_message}"
    return ToolStatus(name=name, available=False, source="missing", message=message)


def _status_for_path(name: str, path: Path, source: str) -> ToolStatus:
    if not path.exists():
        return ToolStatus(
            name=name,
            available=False,
            source=source,
            path=str(path),
            message="configured path does not exist",
        )

    if path.is_dir():
        return ToolStatus(
            name=name,
            available=False,
            source=source,
            path=str(path),
            message="configured path is a directory",
        )

    version, error = _read_tool_version(path)
    if error is not None:
        return ToolStatus(
            name=name,
            available=False,
            source=source,
            path=str(path),
            message=error,
        )

    return ToolStatus(
        name=name,
        available=True,
        source=source,
        path=str(path),
        version=version,
    )


def _read_tool_version(path: Path) -> tuple[str | None, str | None]:
    try:
        completed = subprocess.run(
            [str(path), "-version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return None, "version check timed out"
    except OSError as exc:
        return None, f"could not execute version check: {exc}"

    if completed.returncode != 0:
        output = completed.stderr or completed.stdout
        detail = (
            output.splitlines()[0] if output else f"exit code {completed.returncode}"
        )
        return None, f"version check failed: {detail}"

    output = completed.stdout or completed.stderr
    return output.splitlines()[0] if output else None, None


def _find_static_ffmpeg_tool(name: str) -> tuple[Path | None, str | None]:
    try:
        from static_ffmpeg import run
    except Exception as exc:  # pragma: no cover - depends on optional provider state
        return None, str(exc)

    get_platform_dir = getattr(run, "get_platform_dir", None)
    if not callable(get_platform_dir):
        return None, "get_platform_dir is unavailable"

    try:
        static_dir = Path(get_platform_dir())
    except Exception as exc:  # pragma: no cover - depends on optional provider state
        return None, str(exc)

    executable_name = f"{name}.exe" if sys.platform == "win32" else name
    static_path = static_dir / executable_name
    if static_path.exists():
        return static_path, None

    return None, f"{static_path} is unavailable"
