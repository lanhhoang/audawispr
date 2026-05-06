"""Runtime diagnostics for local audawispr execution."""

from __future__ import annotations

import json
import os
import platform as _platform
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
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
    """Find a media binary from env vars, PATH, audawispr cache, or static-ffmpeg."""
    explicit_path = os.environ.get(env_var)
    if explicit_path:
        return _status_for_path(name, Path(explicit_path), f"{env_var}")

    path_tool = which(name)
    if path_tool is not None:
        return _status_for_path(name, Path(path_tool), "PATH")

    cached_tool, static_message = _find_cached_ffmpeg_tool(name)
    if cached_tool is not None:
        # Determine actual source — cache or static-ffmpeg fallback
        cache_dir = get_cache_dir()
        platform_key = detect_platform_key()
        cache_prefix = cache_dir / "ffmpeg" / "bin" / platform_key
        source = (
            "audawispr-cache"
            if str(cached_tool).startswith(str(cache_prefix))
            else "static-ffmpeg"
        )
        return _status_for_path(name, cached_tool, source)

    message = (
        "not found in environment variable, PATH, audawispr cache, or static-ffmpeg"
    )
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


def _find_cached_ffmpeg_tool(name: str) -> tuple[Path | None, str | None]:
    """Check audawispr shared cache, then static-ffmpeg venv dir."""
    cache_dir = get_cache_dir()
    platform_key = detect_platform_key()
    executable_name = f"{name}.exe" if sys.platform == "win32" else name
    cache_path = cache_dir / "ffmpeg" / "bin" / platform_key / executable_name
    if cache_path.exists():
        return cache_path, None
    return _find_static_ffmpeg_tool(name)


def copy_ffmpeg_to_cache(
    ffmpeg_src: Path,
    ffprobe_src: Path,
    *,
    cache_dir: Path,
) -> tuple[Path, Path]:
    """Copy binaries to audawispr shared cache dir, set executable bits."""
    platform_key = detect_platform_key()
    bin_dir = cache_dir / "ffmpeg" / "bin" / platform_key
    bin_dir.mkdir(parents=True, exist_ok=True)

    def _exe_name(name: str) -> str:
        return f"{name}.exe" if sys.platform == "win32" else name

    ffmpeg_dst = bin_dir / _exe_name("ffmpeg")
    ffprobe_dst = bin_dir / _exe_name("ffprobe")

    shutil.copy2(ffmpeg_src, ffmpeg_dst)
    shutil.copy2(ffprobe_src, ffprobe_dst)

    if sys.platform != "win32":
        mode = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        ffmpeg_dst.chmod(ffmpeg_dst.stat().st_mode | mode)
        ffprobe_dst.chmod(ffprobe_dst.stat().st_mode | mode)

    return ffmpeg_dst, ffprobe_dst


def _write_cache_metadata(
    *,
    ffmpeg_status: ToolStatus,
    ffprobe_status: ToolStatus,
    cache_dir: Path,
) -> None:
    """Write metadata.json to the FFmpeg cache directory."""
    metadata = {
        "platform_key": detect_platform_key(),
        "installed_at": datetime.now(UTC).isoformat(),
        "ffmpeg": {
            "path": ffmpeg_status.path,
            "version": ffmpeg_status.version,
        },
        "ffprobe": {
            "path": ffprobe_status.path,
            "version": ffprobe_status.version,
        },
    }
    meta_path = cache_dir / "ffmpeg" / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def install_ffmpeg(
    *,
    prefer_system: bool = True,
    force: bool = False,
) -> FFmpegInstallResult:
    """Download FFmpeg/FFprobe via static-ffmpeg, copy to audawispr shared cache.

    Behavior:
      - System FFmpeg + prefer_system=True → skip, source="system"
      - Cache exists + force=False          → skip, source="audawispr-cache"
      - Otherwise                           → download + copy to cache

    Raises: DependencyError on unsupported platform, network failure, or corrupt ZIP.
    """
    from audawispr.core.errors import DependencyError

    cache_dir = get_cache_dir()
    platform_key = detect_platform_key()

    # Check system FFmpeg
    if prefer_system:
        system_ffmpeg = shutil.which("ffmpeg")
        system_ffprobe = shutil.which("ffprobe")
        if system_ffmpeg and system_ffprobe:
            ffmpeg_s = _status_for_path("ffmpeg", Path(system_ffmpeg), "system")
            ffprobe_s = _status_for_path("ffprobe", Path(system_ffprobe), "system")
            return FFmpegInstallResult(
                ffmpeg=ffmpeg_s,
                ffprobe=ffprobe_s,
                installed=False,
                cache_dir=str(cache_dir),
                platform_key=platform_key,
                source="system",
            )

    # Check audawispr cache
    if not force:
        cached_ffmpeg, _ = _find_cached_ffmpeg_tool("ffmpeg")
        cached_ffprobe, _ = _find_cached_ffmpeg_tool("ffprobe")
        if cached_ffmpeg and cached_ffprobe:
            ffmpeg_s = _status_for_path("ffmpeg", cached_ffmpeg, "audawispr-cache")
            ffprobe_s = _status_for_path("ffprobe", cached_ffprobe, "audawispr-cache")
            if ffmpeg_s.available and ffprobe_s.available:
                return FFmpegInstallResult(
                    ffmpeg=ffmpeg_s,
                    ffprobe=ffprobe_s,
                    installed=False,
                    cache_dir=str(cache_dir),
                    platform_key=platform_key,
                    source="audawispr-cache",
                )

    # Download via static-ffmpeg
    try:
        from static_ffmpeg import run
    except ImportError as exc:
        raise DependencyError(
            "static-ffmpeg is required to install FFmpeg binaries. "
            "Run `uv sync` to install dependencies."
        ) from exc

    try:
        ffmpeg_path, ffprobe_path = run.get_or_fetch_platform_executables_else_raise()
    except OSError as exc:
        if "implement" in str(exc):
            raise DependencyError(
                f"FFmpeg is not available for your platform ({platform_key}). "
                f"Set {FFMPEG_ENV} to use a custom binary."
            ) from exc
        raise DependencyError(f"Failed to download FFmpeg binaries: {exc}") from exc
    except Exception as exc:
        raise DependencyError(f"Failed to download FFmpeg binaries: {exc}") from exc

    # Copy to audawispr shared cache
    cached_paths = copy_ffmpeg_to_cache(
        Path(ffmpeg_path),
        Path(ffprobe_path),
        cache_dir=cache_dir,
    )

    # Build result
    ffmpeg_s = _status_for_path("ffmpeg", cached_paths[0], "audawispr-cache")
    ffprobe_s = _status_for_path("ffprobe", cached_paths[1], "audawispr-cache")

    _write_cache_metadata(
        ffmpeg_status=ffmpeg_s,
        ffprobe_status=ffprobe_s,
        cache_dir=cache_dir,
    )

    if not ffmpeg_s.available or not ffprobe_s.available:
        raise DependencyError(
            f"Installed FFmpeg binaries could not be verified. "
            f"ffmpeg={'ok' if ffmpeg_s.available else 'MISSING'} at {cached_paths[0]}, "
            f"ffprobe={'ok' if ffprobe_s.available else 'MISSING'} at {cached_paths[1]}"
        )

    return FFmpegInstallResult(
        ffmpeg=ffmpeg_s,
        ffprobe=ffprobe_s,
        installed=True,
        cache_dir=str(cache_dir),
        platform_key=platform_key,
        source="audawispr-cache",
    )


def ensure_ffmpeg() -> Path:
    """Find ffmpeg, auto-installing via static-ffmpeg if needed.

    Resolution: AUDAWISPR_FFMPEG → PATH → audawispr cache → static-ffmpeg install.

    Returns: Absolute path to ffmpeg executable.
    Raises: DependencyError if ffmpeg cannot be found or installed.
    """
    from audawispr.core.errors import DependencyError

    env_path = os.environ.get(FFMPEG_ENV)
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p
        if p.exists():
            raise DependencyError(f"{FFMPEG_ENV}={env_path} is not a regular file")
        raise DependencyError(
            f"{FFMPEG_ENV}={env_path} does not exist. "
            f"Unset the variable or point it to a valid FFmpeg binary."
        )

    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return Path(which_ffmpeg)

    cached, _ = _find_cached_ffmpeg_tool("ffmpeg")
    if cached:
        return cached

    result = install_ffmpeg()
    if not result.ffmpeg.available or result.ffmpeg.path is None:
        raise DependencyError(
            f"FFmpeg could not be installed. "
            f"Install manually or set {FFMPEG_ENV} to point to an FFmpeg binary."
        )
    return Path(result.ffmpeg.path)


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
