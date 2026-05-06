"""Runtime diagnostics for local audawispr execution."""

from __future__ import annotations

import os
import platform as _platform
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
class WhisperModelStatus:
    """Cache status for a specific Whisper model size."""

    cached: bool
    model_size: str
    cache_path: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class FFmpegInstallResult:
    """Result of an FFmpeg/FFprobe installation attempt."""

    ffmpeg: ToolStatus
    ffprobe: ToolStatus
    installed: bool
    cache_dir: str
    platform_key: str
    source: str


@dataclass(frozen=True)
class DiagnosticsReport:
    """Current local runtime readiness report."""

    package_version: str
    python_version: str
    platform_key: str = ""
    cache_dir: str = ""
    ffmpeg_cache_dir: str | None = None
    tools: tuple[ToolStatus, ...] = ()
    whisper: WhisperModelStatus | None = None


def collect_diagnostics() -> DiagnosticsReport:
    """Collect local package, Python, FFmpeg, FFprobe, and Whisper readiness."""
    return DiagnosticsReport(
        package_version=__version__,
        python_version=sys.version.split()[0],
        platform_key=detect_platform_key(),
        cache_dir=str(get_cache_dir()),
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
            [str(path), "-nostdin", "-version"],
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
    except ImportError as exc:  # pragma: no cover - depends on optional provider state
        return None, str(exc)

    get_platform_dir = getattr(run, "get_platform_dir", None)
    if not callable(get_platform_dir):
        return None, "get_platform_dir is unavailable"

    try:
        static_dir = Path(get_platform_dir())
    except ImportError as exc:  # pragma: no cover - depends on optional provider state
        return None, str(exc)

    executable_name = f"{name}.exe" if sys.platform == "win32" else name
    static_path = static_dir / executable_name
    if static_path.exists():
        return static_path, None

    return None, f"{static_path} is unavailable"


CACHE_DIR_ENV = "AUDAWISPR_CACHE_DIR"


def _safe_home() -> Path:
    """Return Path.home() with a fallback for restricted environments."""
    try:
        return Path.home()
    except RuntimeError:
        return Path(os.environ.get("HOME", "/tmp"))


def get_cache_dir() -> Path:
    """Platform-appropriate audawispr cache directory.

    Override with ``AUDAWISPR_CACHE_DIR`` env var.
    macOS: ``~/Library/Caches/audawispr``
    Linux: ``~/.cache/audawispr``
    Windows: ``%LOCALAPPDATA%/audawispr/cache``

    An empty value for any env var is treated as unset and falls through
    to the platform default.
    """
    if override := os.environ.get(CACHE_DIR_ENV):
        path = Path(override).expanduser().resolve()
        if not path.is_dir() and path.suffix:
            path = path.parent
        return path
    home = _safe_home()
    if sys.platform == "darwin":
        return home / "Library" / "Caches" / "audawispr"
    if sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        return Path(root) / "audawispr" / "cache"
    root = os.environ.get("XDG_CACHE_HOME") or str(home / ".cache")
    return Path(root) / "audawispr"


def detect_platform_key() -> str:
    """Static-ffmpeg compatible platform key.

    Returns: ``"darwin_arm64"``, ``"darwin"``, ``"linux"``,
    ``"linux_arm64"``, ``"win32"``, or the raw ``sys.platform`` value.

    ``"linux"`` is returned for all non-ARM Linux architectures
    (including x86_64, i686, and armv7l).
    """
    if sys.platform == "win32":
        return "win32"
    machine = _platform.machine().lower()
    is_arm = machine in {"arm64", "aarch64"}
    if sys.platform == "darwin":
        return "darwin_arm64" if is_arm else "darwin"
    if sys.platform == "linux":
        return "linux_arm64" if is_arm else "linux"
    return sys.platform
