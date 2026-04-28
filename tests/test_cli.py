from typer.testing import CliRunner

from audawispr.__about__ import __version__
from audawispr.cli import app

runner = CliRunner()


def test_help_displays_cli_name() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "audawispr" in result.stdout
    assert "doctor" in result.stdout


def test_version_displays_package_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"audawispr {__version__}" in result.stdout


def test_doctor_displays_output_shape() -> None:
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "audawispr doctor" in result.stdout
    assert "Package: audawispr" in result.stdout
    assert "Python:" in result.stdout
    assert "ffmpeg:" in result.stdout
    assert "ffprobe:" in result.stdout
