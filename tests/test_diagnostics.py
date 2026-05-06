import sys
from pathlib import Path

from audawispr.core import diagnostics
from audawispr.core.errors import AudawisprError, DependencyError


def test_find_media_tool_reports_missing_without_crashing(
    monkeypatch,
) -> None:
    monkeypatch.delenv("AUDAWISPR_FFMPEG", raising=False)
    monkeypatch.setattr(
        diagnostics,
        "_find_static_ffmpeg_tool",
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
