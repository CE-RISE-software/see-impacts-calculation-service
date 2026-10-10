"""Import the pinned public BONSAI IO release into a prepared Brightway project."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from .compatibility import _declared_project_name


SOURCE_SHA256 = {
    "extensions_value_table.gzip": "741ab544cd53bc323c50c38e2491d813a13b9999331b44d900d020473b38bb5c",
    "index_table_extensions.gzip": "9a35f45b0b6a777b48c5421faa13a528dd7a349caba018b2f115472c4da0be6a",
    "index_table_hiot.gzip": "2d7fb067c4576eb39813ce89d2dca60fa59e37c2dbf440131e06663d2208ca03",
    "io_metadata.json": "19cf30258987bdf75ed9d76f2574f87bbe9af3ced55e0c86b34473b967e9fce8",
    "product_value_table.gzip": "3fd45e81805f1104edbfe71027a8c76f44398f1c21492bff5ad268f0a4000c1f",
    "technosphere_value_table.gzip": "af65ba7b14acd821db6dcac75a81c8cb9aee7aa7b65b7ab9584b41abcbcd0776",
}


class BonsaiImportError(RuntimeError):
    """The pinned BONSAI release cannot be imported into this project."""


def verify_source(source_dir: Path) -> None:
    """Check the six published release files before touching the project."""

    for name, expected in SOURCE_SHA256.items():
        path = source_dir / name
        if not path.is_file() or path.is_symlink():
            raise BonsaiImportError(f"BONSAI source file is missing: {path}")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != expected:
            raise BonsaiImportError(f"BONSAI source file checksum differs: {path}")


def import_bonsai(
    source_dir: Path,
    project_dir: Path,
    project_name: str,
    database_name: str = "bonsai",
) -> int:
    """Replace the seed BONSAI database with release 3.8-beta2 (bw)."""

    verify_source(source_dir)
    project_dir = project_dir.resolve(strict=True)
    if _declared_project_name(project_dir) != project_name:
        raise BonsaiImportError("Prepared Brightway project name differs from configuration.")
    if os.environ.get("BRIGHTWAY2_DIR"):
        raise BonsaiImportError("BRIGHTWAY2_DIR must be unset during background import.")

    with TemporaryDirectory(prefix="bonsai-import-") as temporary:
        temporary_dir = Path(temporary)
        workspace = temporary_dir / "workspace"
        workspace.mkdir()
        source_view = temporary_dir / "source"
        source_view.mkdir()
        for name in SOURCE_SHA256:
            (source_view / name).symlink_to((source_dir / name).resolve(strict=True))
        # The importer uses an older filename for the published HIOT index.
        (source_view / "index_table_technosphere.gzip").symlink_to(
            source_view / "index_table_hiot.gzip"
        )

        os.environ["BRIGHTWAY2_DIR"] = str(workspace)
        try:
            import bw2data as bd
            from bw2data.project import safe_filename
            from bw2io.importers.bonsai import BonsaiImporter
            from bw2io.strategies.bonsai import mapb3

            (workspace / safe_filename(project_name)).symlink_to(
                project_dir, target_is_directory=True
            )
            bd.projects.set_current(project_name, writable=True, update=False)
            for name in (database_name, f"{database_name} biosphere"):
                if name in bd.databases:
                    del bd.databases[name]
            importer = BonsaiImporter(source_view, database_name, b3mapping=mapb3())
            importer.apply_strategies()
            importer.write_database(biosphere="biosphere3")
            metadata = dict(bd.databases[database_name])
            metadata.pop("filepath", None)
            metadata["source_url"] = "https://doi.org/10.5281/zenodo.15421526"
            metadata["source_version"] = "3.8-beta2 (bw)"
            bd.databases[database_name] = metadata
            count = len(bd.Database(database_name))
            if count != 34567 or "biosphere3" not in bd.databases or not bd.methods:
                raise BonsaiImportError("Imported BONSAI background is incomplete.")
            return count
        finally:
            os.environ.pop("BRIGHTWAY2_DIR", None)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import the BONSAI 3.8-beta2 IO release.")
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--project-name", required=True)
    args = parser.parse_args()
    try:
        count = import_bonsai(args.source_dir, args.project_dir, args.project_name)
    except (BonsaiImportError, OSError) as error:
        parser.exit(1, f"{error}\n")
    print(f"Imported {count} BONSAI activities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
