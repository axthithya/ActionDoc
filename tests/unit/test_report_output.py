"""Tests for atomic report-file output."""

from pathlib import Path

import pytest

from actiondoctor.reporting.output import ReportWriteError, write_report_atomic


def test_atomic_output_creates_parents_and_replaces_existing_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "nested" / "report.json"
    target.parent.mkdir()
    target.write_text("old", encoding="utf-8")

    write_report_atomic(target, "new\n")

    assert target.read_text(encoding="utf-8") == "new\n"


def test_failed_atomic_replace_preserves_existing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "report.json"
    target.write_text("old", encoding="utf-8")

    def fail_replace(_source: Path, _target: Path) -> None:
        raise PermissionError("replacement denied")

    monkeypatch.setattr("actiondoctor.reporting.output.os.replace", fail_replace)

    with pytest.raises(ReportWriteError, match="Could not write report"):
        write_report_atomic(target, "new\n")

    assert target.read_text(encoding="utf-8") == "old"
    assert list(tmp_path.glob("*.tmp")) == []


def test_directory_output_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ReportWriteError, match="is a directory"):
        write_report_atomic(tmp_path, "report\n")
