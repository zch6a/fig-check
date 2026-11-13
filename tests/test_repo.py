"""The repository's own promises: the README shows what fig-check prints for the example."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fig_check import cli

ROOT = Path(__file__).resolve().parent.parent


def test_the_readme_output_is_the_examples(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    assert cli.main(["examples/paper"]) == 1
    printed = capsys.readouterr().out.rstrip("\n")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    shown = re.search(r"```\n(fig-check: main\.tex: [\s\S]*?)\n```", readme)
    assert shown and shown.group(1) == printed, "run: fig-check examples/paper, and paste into the README"


def test_the_package_is_typed() -> None:
    root = Path(__file__).resolve().parent.parent
    assert (root / "src" / "fig_check" / "py.typed").is_file()
    assert "dependencies = []" in (root / "pyproject.toml").read_text(encoding="utf-8")
