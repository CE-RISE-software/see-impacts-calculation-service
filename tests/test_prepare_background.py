"""Tests for Docker background-project preparation."""

from __future__ import annotations

import hashlib
import io
import json
import pickle
import sqlite3
import tarfile
import zipfile
from pathlib import Path

import numpy as np
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
    manifest = json.loads((archive.parent / "project.json").read_text())
    with sqlite3.connect(project / "lci/databases.db") as connection:
        actual_counts = dict(connection.execute(
            'SELECT database, COUNT(*) FROM activitydataset GROUP BY database'
        ))
    assert actual_counts == manifest["databases"] == {
        "BONSAI": 49978, "BONSAI biosphere": 7, "ef31_biosphere": 93993,
    }
    methods = json.loads((project / "methods.json").read_text())
    assert len(methods) == 25
    for method_name, metadata in methods:
        assert method_name[0] == "EF 3.1"
        factors_path = project / "intermediate" / (metadata["abbreviation"] + ".pickle")
        with factors_path.open("rb") as stream:
            factors = pickle.load(stream)
        assert len(factors) == metadata["num_cfs"] > 0
    for name, expected in manifest["source_processed_sha256"].items():
        with (project / "processed" / name).open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == expected, name
    climate = next(metadata for name, metadata in methods if name[1] == "Climate change")
    with zipfile.ZipFile(project / "processed" / (climate["abbreviation"] + ".zip")) as package:
        resources = json.loads(package.read("datapackage.json"))["resources"]
        with package.open(next(r["path"] for r in resources if r["kind"] == "data")) as stream:
            values = np.load(stream)
    assert np.isfinite(values).all()
    units = {name[1]: metadata["unit"] for name, metadata in methods}
    assert units["Resource use, fossils"] == "MJ"
    assert units["Resource use, minerals and metals"] == "kg Sb-Eq"
    with pytest.raises(BackgroundPreparationError, match="already exists"):
        prepare_background(archive, output, "cerise_bonsai")


def test_bundled_archive_matches_recorded_checksum() -> None:
    background = Path(__file__).resolve().parents[1] / "data/background"
    manifest = json.loads((background / "project.json").read_text())
    with (background / manifest["archive"]).open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == manifest["archive_sha256"]


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
