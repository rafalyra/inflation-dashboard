from pathlib import Path

from typer.testing import CliRunner

from inflation.cli import app

runner = CliRunner()


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ["fetch", "validate", "compute", "export", "run", "due", "backfill", "calendar"]:
        assert command in result.output


def test_due_with_repo_config(repo_config_dir: Path) -> None:
    result = runner.invoke(app, ["due", "--config-dir", str(repo_config_dir)])
    assert result.exit_code == 0


def test_unknown_country_rejected(repo_config_dir: Path) -> None:
    result = runner.invoke(app, ["compute", "zz", "--config-dir", str(repo_config_dir)])
    assert result.exit_code == 2
