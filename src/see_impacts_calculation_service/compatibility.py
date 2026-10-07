"""Brightway project compatibility probe for the locally supplied background data."""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import redirect_stdout
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import RuntimeConfig


class BrightwayCompatibilityError(RuntimeError):
    """The installed Brightway runtime cannot safely inspect the supplied project."""


@dataclass(frozen=True)
class DatabaseSummary:
    name: str
    backend: str | None
    format: str | None
    activity_count: int | None
    sample_key: tuple[str, str]
    sample_exchange_count: int
    datapackage_resource_count: int


@dataclass(frozen=True)
class CompatibilityReport:
    project_directory: str
    declared_project_name: str
    bw2data_version: str
    bw2calc_version: str
    databases: list[DatabaseSummary]
    method_count: int
    method_examples: list[list[str]]
    sample_method: list[str]
    sample_method_factor_count: int


def _version_string(value: Any) -> str:
    if isinstance(value, tuple):
        return ".".join(str(part) for part in value)
    return str(value)


def _declared_project_name(project_dir: Path) -> str:
    metadata_path = project_dir / ".project-name.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise BrightwayCompatibilityError(
            f"Brightway project metadata is missing: {metadata_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise BrightwayCompatibilityError(
            f"Brightway project metadata is invalid JSON: {metadata_path}"
        ) from error

    name = metadata.get("name")
    if not isinstance(name, str) or not name:
        raise BrightwayCompatibilityError(
            f"Brightway project metadata has no usable name: {metadata_path}"
        )
    return name


def _load_brightway_project(
    project_dir: Path, project_name: str, workspace_dir: Path
) -> tuple[Any, Any]:
    """Activate the supplied project through a writable Brightway 2.5 workspace.

    Brightway stores its registry in a base directory, while the supplied project is
    an immutable source artifact. A symlink exposes that artifact under Brightway's
    expected hashed directory name without writing to the source data.
    """

    workspace_dir.mkdir(parents=True, exist_ok=True)
    configured_workspace = os.environ.get("BRIGHTWAY2_DIR")
    if configured_workspace and Path(configured_workspace).resolve() != workspace_dir:
        raise BrightwayCompatibilityError(
            "BRIGHTWAY2_DIR conflicts with BRIGHTWAY_WORKSPACE_DIR; use one workspace."
        )
    os.environ["BRIGHTWAY2_DIR"] = str(workspace_dir)

    try:
        import bw2calc
        import bw2data
        from bw2data.project import safe_filename

        linked_project_dir = workspace_dir / safe_filename(project_name)
        if linked_project_dir.exists() or linked_project_dir.is_symlink():
            if not linked_project_dir.is_symlink() or linked_project_dir.resolve() != project_dir:
                raise BrightwayCompatibilityError(
                    f"Brightway workspace already contains a different project path: {linked_project_dir}"
                )
        else:
            linked_project_dir.symlink_to(project_dir, target_is_directory=True)

        bw2data.projects.set_current(project_name, writable=False, update=False)
    except Exception as error:  # Brightway uses several backend-specific exceptions.
        if isinstance(error, BrightwayCompatibilityError):
            raise
        raise BrightwayCompatibilityError(
            "Brightway 2.5 could not activate the supplied project. "
            "The project may require an import step or a different Brightway release."
        ) from error

    return bw2data, bw2calc


def _verified_project(
    project_dir: Path,
    workspace_dir: Path,
    expected_project_name: str | None = None,
) -> tuple[Any, Any, str, Path]:
    resolved_project_dir = project_dir.resolve()
    if not resolved_project_dir.is_dir():
        raise BrightwayCompatibilityError(
            f"Brightway project directory does not exist: {resolved_project_dir}"
        )

    declared_name = _declared_project_name(resolved_project_dir)
    if expected_project_name and declared_name != expected_project_name:
        raise BrightwayCompatibilityError(
            "Configured background project name does not match .project-name.json: "
            f"{expected_project_name!r} != {declared_name!r}"
        )

    bw2data, bw2calc = _load_brightway_project(
        resolved_project_dir, declared_name, workspace_dir.resolve()
    )
    return bw2data, bw2calc, declared_name, resolved_project_dir


def list_methods(
    project_dir: Path,
    workspace_dir: Path,
    expected_project_name: str | None = None,
) -> tuple[str, list[list[str]]]:
    """List all registered impact-method identifiers in the supplied project."""

    bw2data, _, declared_name, _ = _verified_project(
        project_dir, workspace_dir, expected_project_name
    )
    try:
        methods = [list(method) for method in sorted(bw2data.methods)]
    except Exception as error:
        raise BrightwayCompatibilityError(
            "Brightway could not list impact methods from the supplied background."
        ) from error
    return declared_name, methods


def run_probe(
    project_dir: Path,
    workspace_dir: Path,
    expected_project_name: str | None = None,
) -> CompatibilityReport:
    """Read background databases, exchanges, datapackages, and method factors.

    This intentionally does not create a foreground database or run an LCIA demand.
    """

    bw2data, bw2calc, declared_name, resolved_project_dir = _verified_project(
        project_dir, workspace_dir, expected_project_name
    )
    try:
        databases = []
        for name, metadata in sorted(bw2data.databases.items()):
            database = bw2data.Database(name)
            sample = next(iter(database))
            databases.append(
                DatabaseSummary(
                    name=name,
                    backend=metadata.get("backend"),
                    format=metadata.get("format"),
                    activity_count=metadata.get("number"),
                    sample_key=sample.key,
                    sample_exchange_count=sum(1 for _ in sample.exchanges()),
                    datapackage_resource_count=len(database.datapackage().resources),
                )
            )
        methods = sorted(bw2data.methods)
        sample_method = methods[0]
        sample_method_factor_count = len(bw2data.Method(sample_method).load())
    except (StopIteration, IndexError) as error:
        raise BrightwayCompatibilityError(
            "The supplied background has an empty database or no impact method."
        ) from error
    except Exception as error:
        raise BrightwayCompatibilityError(
            "Brightway could not read a database record, its exchanges, a processed "
            "datapackage, or an impact method from the supplied background."
        ) from error

    return CompatibilityReport(
        project_directory=str(resolved_project_dir),
        declared_project_name=declared_name,
        bw2data_version=_version_string(getattr(bw2data, "__version__", "unknown")),
        bw2calc_version=_version_string(getattr(bw2calc, "__version__", "unknown")),
        databases=databases,
        method_count=len(bw2data.methods),
        method_examples=[list(method) for method in methods[:5]],
        sample_method=list(sample_method),
        sample_method_factor_count=sample_method_factor_count,
    )


def main() -> int:
    config = RuntimeConfig.from_env()
    parser = argparse.ArgumentParser(
        description="Inspect a Brightway 2.5 background project without running an LCIA."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=config.background_project_dir,
        help="Path to the extracted Brightway project directory.",
    )
    parser.add_argument(
        "--project-name",
        default=config.background_project_name,
        help="Expected name from .project-name.json.",
    )
    parser.add_argument(
        "--workspace-dir",
        type=Path,
        default=config.brightway_workspace_dir,
        help="Writable Brightway registry workspace; source project data is not modified.",
    )
    args = parser.parse_args()

    try:
        with redirect_stdout(sys.stderr):
            report = run_probe(args.project_dir, args.workspace_dir, args.project_name)
    except BrightwayCompatibilityError as error:
        print(f"compatibility probe failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(asdict(report), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
