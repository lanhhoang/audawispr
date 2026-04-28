from pathlib import Path

from audawispr.core import diagnostics


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
