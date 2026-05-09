import sys
from pathlib import Path

import pytest

from audawispr.core import diagnostics
from audawispr.core.errors import AudawisprError, DependencyError


def test_find_media_tool_reports_missing_without_crashing(
    monkeypatch,
) -> None:
    monkeypatch.delenv("AUDAWISPR_FFMPEG", raising=False)
    monkeypatch.setattr(
        diagnostics,
        "_find_cached_ffmpeg_tool",
        lambda _: (None, "unavailable"),
    )

    status = diagnostics.find_media_tool(
        "ffmpeg",
        "AUDAWISPR_FFMPEG",
        which=lambda _: None,
    )

    assert status.name == "ffmpeg"
    assert status.available is False
    assert status.source == "missing"
    assert "not found" in str(status.message)


def test_find_media_tool_prefers_explicit_env_path(monkeypatch, tmp_path: Path) -> None:
    tool_path = tmp_path / "ffmpeg.exe"
    tool_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("AUDAWISPR_FFMPEG", str(tool_path))
    monkeypatch.setattr(
        diagnostics,
        "_read_tool_version",
        lambda _: ("ffmpeg version test", None),
    )

    status = diagnostics.find_media_tool(
        "ffmpeg",
        "AUDAWISPR_FFMPEG",
        which=lambda _: None,
    )

    assert status.available is True
    assert status.source == "AUDAWISPR_FFMPEG"
    assert status.path == str(tool_path)
    assert status.version == "ffmpeg version test"


# --- Platform key ---


def test_detect_platform_key_darwin_arm64(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(diagnostics._platform, "machine", lambda: "arm64")
    assert diagnostics.detect_platform_key() == "darwin_arm64"


def test_detect_platform_key_darwin_x86(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(diagnostics._platform, "machine", lambda: "x86_64")
    assert diagnostics.detect_platform_key() == "darwin"


def test_detect_platform_key_linux_x86(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(diagnostics._platform, "machine", lambda: "x86_64")
    assert diagnostics.detect_platform_key() == "linux"


def test_detect_platform_key_linux_arm64(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(diagnostics._platform, "machine", lambda: "aarch64")
    assert diagnostics.detect_platform_key() == "linux_arm64"


def test_detect_platform_key_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert diagnostics.detect_platform_key() == "win32"


# --- Cache dir ---


def test_get_cache_dir_macos(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.delenv("AUDAWISPR_CACHE_DIR", raising=False)
    result = diagnostics.get_cache_dir()
    assert "Library" in str(result)
    assert "Caches" in str(result)
    assert "audawispr" in str(result)


def test_get_cache_dir_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("AUDAWISPR_CACHE_DIR", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    result = diagnostics.get_cache_dir()
    assert "AppData" in str(result)
    assert "audawispr" in str(result)
    assert "cache" in str(result)


def test_get_cache_dir_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("AUDAWISPR_CACHE_DIR", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    result = diagnostics.get_cache_dir()
    assert ".cache" in str(result)
    assert "audawispr" in str(result)


def test_get_cache_dir_linux_xdg(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("AUDAWISPR_CACHE_DIR", raising=False)
    result = diagnostics.get_cache_dir()
    assert result == tmp_path / "xdg" / "audawispr"


def test_get_cache_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDAWISPR_CACHE_DIR", str(tmp_path / "mine"))
    result = diagnostics.get_cache_dir()
    assert result == tmp_path / "mine"


# --- Error hierarchy ---


def test_dependency_error_is_audawispr_error():
    assert issubclass(DependencyError, AudawisprError)


def test_dependency_error_message():
    err = DependencyError("test message")
    assert str(err) == "test message"


# --- Platform key edge cases ---


def test_detect_platform_key_unknown_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "freebsd")
    assert diagnostics.detect_platform_key() == "freebsd"


def test_detect_platform_key_darwin_machine_uppercase(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(diagnostics._platform, "machine", lambda: "ARM64")
    assert diagnostics.detect_platform_key() == "darwin_arm64"


def test_detect_platform_key_linux_machine_unknown(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(diagnostics._platform, "machine", lambda: "unknown")
    assert diagnostics.detect_platform_key() == "linux"


def test_detect_platform_key_win32_does_not_call_machine(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    # If detect_platform_key() incorrectly called machine(), this mock
    # would fail because win32 returns early before the machine() call.
    monkeypatch.setattr(diagnostics._platform, "machine", lambda: "arm64")
    assert diagnostics.detect_platform_key() == "win32"


# --- Cache dir edge cases ---


def test_get_cache_dir_treats_empty_override_as_unset(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("AUDAWISPR_CACHE_DIR", "")
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    result = diagnostics.get_cache_dir()
    # Empty AUDAWISPR_CACHE_DIR should fall through to XDG default
    assert ".cache" in str(result)
    assert "audawispr" in str(result)


def test_get_cache_dir_treats_empty_xdg_as_unset(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CACHE_HOME", "")
    monkeypatch.delenv("AUDAWISPR_CACHE_DIR", raising=False)
    result = diagnostics.get_cache_dir()
    assert ".cache" in str(result)
    assert "audawispr" in str(result)


def test_get_cache_dir_win32_with_localappdata(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\test\AppData\Local")
    monkeypatch.delenv("AUDAWISPR_CACHE_DIR", raising=False)
    result = diagnostics.get_cache_dir()
    assert "C:\\Users\\test\\AppData\\Local" in str(result)
    assert "audawispr" in str(result)
    assert "cache" in str(result)


def test_get_cache_dir_windows_localappdata_empty(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", "")
    monkeypatch.delenv("AUDAWISPR_CACHE_DIR", raising=False)
    result = diagnostics.get_cache_dir()
    assert "AppData" in str(result)
    assert "audawispr" in str(result)


# --- Dataclass construction ---


def test_ffmpeg_install_result_defaults():
    ffmpeg = diagnostics.ToolStatus(
        name="ffmpeg", available=True, source="test", path="/bin/ffmpeg"
    )
    ffprobe = diagnostics.ToolStatus(
        name="ffprobe", available=True, source="test", path="/bin/ffprobe"
    )
    result = diagnostics.FFmpegInstallResult(
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
        installed=True,
        cache_dir="/cache",
        platform_key="linux",
        source="audawispr-cache",
    )
    assert result.ffmpeg.name == "ffmpeg"
    assert result.installed is True
    assert result.source == "audawispr-cache"


def test_whisper_model_status_defaults():
    status = diagnostics.WhisperModelStatus(
        cached=True,
        model_size="small",
        cache_path="/cache/path",
    )
    assert status.cached is True
    assert status.model_size == "small"
    assert status.cache_path == "/cache/path"
    assert status.message is None  # default


def test_whisper_model_status_message_none_by_default():
    status = diagnostics.WhisperModelStatus(cached=False, model_size="tiny")
    assert status.cached is False
    assert status.message is None


# --- collect_diagnostics populates new fields ---


def test_collect_diagnostics_includes_new_fields(monkeypatch):
    monkeypatch.setattr(
        diagnostics,
        "find_media_tool",
        lambda *a, **kw: diagnostics.ToolStatus(
            name="ffmpeg",
            available=False,
            source="missing",
        ),
    )
    report = diagnostics.collect_diagnostics()
    assert report.platform_key != ""
    assert report.cache_dir != ""


# --- install_ffmpeg ---


def test_install_ffmpeg_downloads_when_missing(monkeypatch, tmp_path):
    """Full download when no system ffmpeg and no cache."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("AUDAWISPR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(diagnostics, "shutil", _ShutilWhichNone())
    monkeypatch.setattr(diagnostics, "_find_cached_ffmpeg_tool", lambda _: (None, None))

    # Mock static-ffmpeg to return fake paths
    monkeypatch.setattr(
        "static_ffmpeg.run.get_or_fetch_platform_executables_else_raise",
        lambda *a, **kw: ("/bin/fake-ffmpeg", "/bin/fake-ffprobe"),
    )

    # Mock copy_ffmpeg_to_cache to create real files for _status_for_path
    def fake_copy(ffmpeg_src, ffprobe_src, *, cache_dir):
        bin_dir = cache_dir / "ffmpeg" / "bin" / "linux"
        bin_dir.mkdir(parents=True, exist_ok=True)
        f = bin_dir / "ffmpeg"
        f.write_text("fake")
        f.chmod(0o755)
        p = bin_dir / "ffprobe"
        p.write_text("fake")
        p.chmod(0o755)
        return (f, p)

    monkeypatch.setattr(diagnostics, "copy_ffmpeg_to_cache", fake_copy)

    # Mock _read_tool_version to pass _status_for_path
    monkeypatch.setattr(
        diagnostics,
        "_read_tool_version",
        lambda _: ("ffmpeg version test", None),
    )

    result = diagnostics.install_ffmpeg()

    assert result.installed is True
    assert result.source == "audawispr-cache"
    assert result.ffmpeg.available is True


class _ShutilWhichNone:
    """Stand-in for shutil with which() always returning None."""

    @staticmethod
    def which(name: str) -> None:
        return None


def test_install_ffmpeg_skips_when_system_found(monkeypatch, tmp_path):
    """System ffmpeg found with prefer_system=True — skip install."""
    monkeypatch.setenv("AUDAWISPR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(diagnostics, "_find_cached_ffmpeg_tool", lambda _: (None, None))

    # Create a fake system ffmpeg path
    system_ffmpeg = tmp_path / "system-ffmpeg"
    system_ffmpeg.write_text("")
    system_ffmpeg.chmod(0o755)
    system_ffprobe = tmp_path / "system-ffprobe"
    system_ffprobe.write_text("")
    system_ffprobe.chmod(0o755)

    # Mock shutil.which to return our fake paths
    def fake_which(name: str) -> str | None:
        if name == "ffmpeg":
            return str(system_ffmpeg)
        if name == "ffprobe":
            return str(system_ffprobe)
        return None

    monkeypatch.setattr(diagnostics.shutil, "which", fake_which)

    # Mock _read_tool_version to pass validation
    monkeypatch.setattr(
        diagnostics,
        "_read_tool_version",
        lambda _: ("ffmpeg version test", None),
    )

    result = diagnostics.install_ffmpeg()

    assert result.installed is False
    assert result.source == "system"
    assert result.ffmpeg.available is True


def test_install_ffmpeg_raises_on_network_failure(monkeypatch, tmp_path):
    """Network failure during download raises DependencyError."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("AUDAWISPR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(diagnostics, "_find_cached_ffmpeg_tool", lambda _: (None, None))

    # Mock static-ffmpeg to fail
    def fake_fail(*a, **kw):
        raise ConnectionError("Network is unreachable")

    monkeypatch.setattr(
        "static_ffmpeg.run.get_or_fetch_platform_executables_else_raise",
        fake_fail,
    )

    with pytest.raises(DependencyError, match="Failed to download"):
        diagnostics.install_ffmpeg()


def test_install_ffmpeg_raises_on_unsupported_platform(monkeypatch, tmp_path):
    """Unsupported platform raises DependencyError."""
    monkeypatch.setenv("AUDAWISPR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(diagnostics, "_find_cached_ffmpeg_tool", lambda _: (None, None))
    monkeypatch.setattr(diagnostics, "_find_static_ffmpeg_tool", lambda _: (None, None))

    # Mock static-ffmpeg to fail with platform error
    def fake_platform_error(*a, **kw):
        raise OSError("Please implement static_ffmpeg for freebsd")

    monkeypatch.setattr(
        "static_ffmpeg.run.get_or_fetch_platform_executables_else_raise",
        fake_platform_error,
    )

    with pytest.raises(DependencyError, match="not available for your platform"):
        diagnostics.install_ffmpeg(prefer_system=False)


# --- check_whisper_model_status ---


def test_check_whisper_model_status_cached(monkeypatch):
    """Model is in local cache."""

    def fake_download(size, local_files_only=True):
        assert local_files_only is True
        return f"/cache/{size}/snapshots/hash"

    monkeypatch.setattr("faster_whisper.utils.download_model", fake_download)

    status = diagnostics.check_whisper_model_status("small")
    assert status.cached is True
    assert status.cache_path == "/cache/small/snapshots/hash"


def test_check_whisper_model_status_not_cached(monkeypatch):
    """Model is not in local cache."""
    from huggingface_hub.errors import LocalEntryNotFoundError

    def fake_download(size, local_files_only=True):
        raise LocalEntryNotFoundError("not found")

    monkeypatch.setattr("faster_whisper.utils.download_model", fake_download)

    status = diagnostics.check_whisper_model_status("small")
    assert status.cached is False
    assert "not cached" in (status.message or "").lower()


def test_check_whisper_model_status_faster_whisper_missing(monkeypatch):
    """faster-whisper is not importable."""
    import builtins

    original_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name.startswith("faster_whisper"):
            raise ImportError("No module named faster_whisper")
        return original_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    status = diagnostics.check_whisper_model_status("small")
    assert status.cached is False
    assert "not installed" in (status.message or "").lower()


def test_check_whisper_model_status_invalid_size(monkeypatch):
    """Invalid model size returns error, not crash."""
    status = diagnostics.check_whisper_model_status("nonexistent")
    assert status.cached is False
    assert "Invalid model size" in (status.message or "")
