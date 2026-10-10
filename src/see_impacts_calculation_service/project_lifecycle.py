"""Run one foreground calculation in a disposable Brightway project."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
from contextlib import redirect_stdout
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .assessment_inputs import ReferenceFlowDemand
from .compatibility import _declared_project_name
from .foreground import (
    ElementaryFlow,
    ExternalInput,
    ExternalTreatment,
    ForegroundActivity,
    ForegroundAssembly,
    ForegroundInput,
    ForegroundOutput,
)
from .foreground_calculation import ForegroundCalculationError, ForegroundImpact
from .singularity import InvolvedActivity, SingularComponent, SingularityDiagnostic


class IsolatedWorkerError(RuntimeError):
    """The disposable Brightway worker failed independently of assessment inputs."""


def _restore_records(record_type: type, records: list[dict[str, Any]], tuple_fields: tuple[str, ...]) -> tuple:
    return tuple(
        record_type(**{
            name: tuple(value) if name in tuple_fields else value
            for name, value in record.items()
        })
        for record in records
    )


def _restore_assembly(data: dict[str, Any]) -> ForegroundAssembly:
    return ForegroundAssembly(
        activities=_restore_records(ForegroundActivity, data["activities"], ("key",)),
        outputs=_restore_records(ForegroundOutput, data["outputs"], ("key", "producer")),
        inputs=_restore_records(
            ForegroundInput, data["inputs"], ("key", "consumer", "provider_output")
        ),
        external_inputs=_restore_records(ExternalInput, data["external_inputs"], ("key", "consumer")),
        external_treatments=_restore_records(
            ExternalTreatment, data["external_treatments"], ("key", "producer")
        ),
        elementary_flows=_restore_records(ElementaryFlow, data["elementary_flows"], ("key", "activity")),
        reference_output=tuple(data["reference_output"]),
        demand=ReferenceFlowDemand(**data["demand"]),
    )


def _restore_diagnostic(data: dict[str, Any]) -> SingularityDiagnostic:
    return SingularityDiagnostic(
        code=data["code"],
        message=data["message"],
        components=tuple(
            SingularComponent(
                activities=tuple(InvolvedActivity(**activity) for activity in component["activities"]),
                reachable_from_request=component["reachable_from_request"],
            )
            for component in data["components"]
        ),
        scope=data["scope"],
    )


async def calculate_isolated_foreground(
    assembly: ForegroundAssembly,
    *,
    project_dir: Path,
    workspace_dir: Path,
    project_name: str,
    background_database_name: str,
    biosphere_database_name: str,
    method: tuple[str, ...],
    timeout_secs: int = 900,
) -> ForegroundImpact:
    """Create a fresh project in another process and discard it after one request."""

    if timeout_secs <= 0:
        raise ValueError("Calculation timeout must be positive.")
    source = project_dir.resolve()
    workspace_root = workspace_dir.resolve()
    if not source.is_dir():
        raise IsolatedWorkerError(f"Prepared Brightway background is missing: {source}")
    if source == workspace_root or source in workspace_root.parents:
        raise IsolatedWorkerError("Request workspace must not be inside the prepared background.")
    requests_dir = workspace_root / "requests"
    requests_dir.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.pop("BRIGHTWAY2_DIR", None)
    with TemporaryDirectory(prefix="compute-", dir=requests_dir) as temporary:
        payload = {
            "assembly": asdict(assembly),
            "project_dir": str(source),
            "request_dir": temporary,
            "project_name": project_name,
            "background_database_name": background_database_name,
            "biosphere_database_name": biosphere_database_name,
            "method": method,
        }
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "see_impacts_calculation_service.project_lifecycle",
                "--worker",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=environment,
            )
        except OSError as error:
            raise IsolatedWorkerError("Isolated Brightway worker could not start.") from error
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(json.dumps(payload).encode()), timeout=timeout_secs
            )
        except asyncio.TimeoutError as error:
            process.kill()
            await process.communicate()
            raise IsolatedWorkerError(
                f"Brightway calculation exceeded the {timeout_secs}-second time limit."
            ) from error
        except asyncio.CancelledError:
            process.kill()
            await process.communicate()
            raise
    if process.returncode != 0:
        raise IsolatedWorkerError(
            f"Isolated Brightway worker exited with status {process.returncode}."
        )
    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise IsolatedWorkerError("Isolated Brightway worker returned an invalid response.") from error
    if response.get("status") == "error":
        diagnostic = response.get("diagnostic")
        raise ForegroundCalculationError(
            response["message"],
            diagnostic=_restore_diagnostic(diagnostic) if diagnostic else None,
        )
    if response.get("status") != "ok":
        raise IsolatedWorkerError("Isolated Brightway worker returned an unknown status.")
    impact = response["impact"]
    impact["method"] = tuple(impact["method"])
    return ForegroundImpact(**impact)


def _worker(payload: dict[str, Any]) -> ForegroundImpact:
    from .foreground_calculation import calculate_foreground

    source = Path(payload["project_dir"])
    request_root = Path(payload["request_dir"])
    if not source.is_dir():
        raise IsolatedWorkerError(f"Prepared Brightway background is missing: {source}")
    if _declared_project_name(source) != payload["project_name"]:
        raise IsolatedWorkerError("Prepared Brightway project name does not match its metadata.")
    request_project = request_root / "project"
    shutil.copytree(source, request_project)
    return calculate_foreground(
        _restore_assembly(payload["assembly"]),
        project_dir=request_project,
        workspace_dir=request_root / "brightway",
        project_name=payload["project_name"],
        background_database_name=payload["background_database_name"],
        biosphere_database_name=payload["biosphere_database_name"],
        method=tuple(payload["method"]),
    )


def main() -> int:
    if sys.argv[1:] != ["--worker"]:
        return 2
    payload = json.load(sys.stdin)
    try:
        with redirect_stdout(sys.stderr):
            impact = _worker(payload)
    except ForegroundCalculationError as error:
        print(json.dumps({
            "status": "error",
            "message": str(error),
            "diagnostic": asdict(error.diagnostic) if error.diagnostic else None,
        }))
        return 0
    print(json.dumps({"status": "ok", "impact": asdict(impact)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
