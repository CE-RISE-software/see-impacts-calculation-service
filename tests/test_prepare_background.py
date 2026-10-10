"""Tests for Docker background-project preparation."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from see_impacts_calculation_service.prepare_background import (
    BackgroundPreparationError,
    prepare_background,
)


def _archive(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w:gz") as output:
        directory = tarfile.TarInfo("project")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o755
        output.addfile(directory)
        for name, content in members.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            entry.mode = 0o644
            output.addfile(entry, io.BytesIO(content))


def test_rejects_unsafe_archive_before_extraction(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.tar.gz"
    _archive(archive, {"project/../../outside": b"no"})

    with pytest.raises(BackgroundPreparationError, match="one project directory"):
        prepare_background(archive, tmp_path / "output", "project")

    assert not (tmp_path / "outside").exists()


def test_rejects_project_name_mismatch_without_publishing(tmp_path: Path) -> None:
    archive = tmp_path / "wrong-name.tar.gz"
    _archive(archive, {"project/.project-name.json": b'{"name":"other"}'})

    with pytest.raises(BackgroundPreparationError, match="does not match"):
        prepare_background(archive, tmp_path / "output", "project")

    assert not (tmp_path / "output" / "project").exists()


def test_prepares_bundled_brightway_project(tmp_path: Path) -> None:
    archive = Path(__file__).resolve().parents[1] / "data/background/cerise_bonsai.tar.gz"
    output = tmp_path / "projects"

    project = prepare_background(archive, output, "cerise_bonsai")

    assert project.is_dir()
    assert (project / ".project-name.json").exists()
    with pytest.raises(BackgroundPreparationError, match="already exists"):
        prepare_background(archive, output, "cerise_bonsai")


def test_rejects_missing_required_database(tmp_path: Path) -> None:
    archive = Path(__file__).resolve().parents[1] / "data/background/cerise_bonsai.tar.gz"
    output = tmp_path / "projects"

    with pytest.raises(BackgroundPreparationError, match="required database"):
        prepare_background(
            archive,
            output,
            "cerise_bonsai",
            background_database_name="missing",
        )

    assert not any(output.iterdir())
