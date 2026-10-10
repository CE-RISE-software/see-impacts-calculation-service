"""Checks for the pinned public BONSAI IO release."""

from pathlib import Path

import pytest

from see_impacts_calculation_service.import_bonsai import (
    BonsaiImportError,
    SOURCE_SHA256,
    verify_source,
)


def test_bundled_release_matches_published_files() -> None:
    source = Path(__file__).resolve().parents[1] / "data/background/bonsai-3.8-beta2"

    verify_source(source)

    assert {path.name for path in source.iterdir()} == set(SOURCE_SHA256)


def test_rejects_missing_release_file(tmp_path: Path) -> None:
    with pytest.raises(BonsaiImportError, match="missing"):
        verify_source(tmp_path)


def test_rejects_changed_release_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "io_metadata.json").write_text("changed", encoding="utf-8")
    monkeypatch.setattr(
        "see_impacts_calculation_service.import_bonsai.SOURCE_SHA256",
        {"io_metadata.json": SOURCE_SHA256["io_metadata.json"]},
    )

    with pytest.raises(BonsaiImportError, match="checksum differs"):
        verify_source(tmp_path)
