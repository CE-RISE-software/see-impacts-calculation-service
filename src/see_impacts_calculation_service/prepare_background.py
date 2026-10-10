"""Prepare and verify the bundled Brightway background project."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from .compatibility import BrightwayCompatibilityError, _declared_project_name


class BackgroundPreparationError(RuntimeError):
    """The supplied archive cannot provide a usable Brightway project."""


def _verify_project(
    project: Path,
    workspace: Path,
    project_name: str,
    background_database_name: str,
    biosphere_database_name: str,
) -> None:
    try:
        databases = json.loads((project / "databases.json").read_text(encoding="utf-8"))
        methods = json.loads((project / "methods.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BackgroundPreparationError("Brightway project registry is unreadable.") from error
    if not isinstance(databases, dict) or not isinstance(methods, list):
        raise BackgroundPreparationError("Brightway project registry is invalid.")
    if not {background_database_name, biosphere_database_name}.issubset(databases) or not methods:
        raise BackgroundPreparationError(
            "Brightway background lacks a required database or impact method."
        )
    environment = os.environ.copy()
    environment.pop("BRIGHTWAY2_DIR", None)
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "see_impacts_calculation_service.compatibility",
                "--project-dir",
                str(project),
                "--workspace-dir",
                str(workspace),
                "--project-name",
                project_name,
            ],
            capture_output=True,
            check=False,
            env=environment,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BackgroundPreparationError("Brightway compatibility probe could not finish.") from error
    if result.returncode:
        raise BackgroundPreparationError("Brightway could not read the prepared background.")


def prepare_background(
    archive: Path,
    destination: Path,
    project_name: str,
    *,
    background_database_name: str = "bonsai",
    biosphere_database_name: str = "biosphere3",
) -> Path:
    """Extract, probe, and publish a project without leaving partial output."""

    destination.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(archive, "r:gz") as source:
            members = source.getmembers()
            roots = {Path(member.name).parts[0] for member in members if member.name}
            if len(roots) != 1 or any(
                not (member.isfile() or member.isdir())
                or member.name.startswith("/")
                or ".." in Path(member.name).parts
                for member in members
            ):
                raise BackgroundPreparationError(
                    "Brightway archive must contain one project directory and only regular files."
                )
            root = next(iter(roots))
            if not any(member.isdir() and member.name.rstrip("/") == root for member in members):
                raise BackgroundPreparationError("Brightway archive has no project directory.")
            target = destination / root
            if target.exists():
                raise BackgroundPreparationError(f"Brightway project already exists: {target}")
            with TemporaryDirectory(prefix="prepare-", dir=destination) as temporary:
                temporary_root = Path(temporary)
                source.extractall(temporary_root, filter="data")
                project = temporary_root / root
                if _declared_project_name(project) != project_name:
                    raise BackgroundPreparationError(
                        "Brightway archive project name does not match the configured name."
                    )
                _verify_project(
                    project,
                    temporary_root / "workspace",
                    project_name,
                    background_database_name,
                    biosphere_database_name,
                )
                os.replace(project, target)
            return target
    except (OSError, tarfile.TarError, BrightwayCompatibilityError) as error:
        raise BackgroundPreparationError(f"Brightway project preparation failed: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the bundled Brightway project.")
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--background-database", default="bonsai")
    parser.add_argument("--biosphere-database", default="biosphere3")
    args = parser.parse_args()
    try:
        print(
            prepare_background(
                args.archive,
                args.destination,
                args.project_name,
                background_database_name=args.background_database,
                biosphere_database_name=args.biosphere_database,
            )
        )
    except BackgroundPreparationError as error:
        parser.exit(1, f"{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
