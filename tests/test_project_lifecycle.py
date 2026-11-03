import asyncio
import json
import logging
from dataclasses import asdict
from unittest.mock import Mock

import pytest

from see_impacts_calculation_service.assessment_inputs import ReferenceFlowDemand
from see_impacts_calculation_service.foreground import ForegroundAssembly
from see_impacts_calculation_service.foreground_calculation import ForegroundImpact, ImpactIndicator
import see_impacts_calculation_service.project_lifecycle as lifecycle
from see_impacts_calculation_service.project_lifecycle import (
    IsolatedWorkerError,
    calculate_isolated_foreground,
)


@pytest.mark.parametrize(
    ("returncode", "stdout"),
    [(1, b""), (0, b"not json"), (0, b'{"status": "unknown"}')],
)
def test_worker_stderr_is_logged_but_not_returned(
    tmp_path, monkeypatch, caplog, returncode, stdout
):
    monkeypatch.delenv("OPENBLAS_NUM_THREADS", raising=False)
    monkeypatch.delenv("OMP_NUM_THREADS", raising=False)
    monkeypatch.setenv("MKL_NUM_THREADS", "3")

    class FailedProcess:
        def __init__(self):
            self.returncode = returncode

        async def communicate(self, payload):
            return stdout, b"Traceback: worker import failed\n"

    async def start_worker(*args, **kwargs):
        assert kwargs["env"]["OPENBLAS_NUM_THREADS"] == "1"
        assert kwargs["env"]["OMP_NUM_THREADS"] == "1"
        assert kwargs["env"]["MKL_NUM_THREADS"] == "3"
        return FailedProcess()

    monkeypatch.setattr(
        "see_impacts_calculation_service.project_lifecycle.asyncio.create_subprocess_exec",
        start_worker,
    )
    project = tmp_path / "background"
    project.mkdir()
    assembly = ForegroundAssembly(
        activities=(),
        outputs=(),
        inputs=(),
        external_inputs=(),
        external_treatments=(),
        elementary_flows=(),
        reference_output=("dataset", "flow"),
        demand=ReferenceFlowDemand("system", "dataset", "activity", "flow", 1.0, "kg", 1.0),
    )

    with caplog.at_level(logging.ERROR), pytest.raises(IsolatedWorkerError) as error:
        asyncio.run(
            calculate_isolated_foreground(
                assembly,
                project_dir=project,
                workspace_dir=tmp_path / "workspace",
                project_name="example",
                background_database_name="background",
                biosphere_database_name="biosphere",
            )
        )

    assert "worker import failed" in caplog.text
    assert "worker import failed" not in str(error.value)
    assert list((tmp_path / "workspace" / "requests").iterdir()) == []


def test_all_indicators_share_one_project_copy(tmp_path, monkeypatch):
    source = tmp_path / "background"
    source.mkdir()
    (source / ".project-name.json").write_text(json.dumps({"name": "synthetic"}))
    assembly = ForegroundAssembly(
        activities=(), outputs=(), inputs=(), external_inputs=(), external_treatments=(),
        elementary_flows=(), reference_output=("dataset", "flow"),
        demand=ReferenceFlowDemand("system", "dataset", "activity", "flow", 1.0, "kg", 1.0),
    )
    impact = ForegroundImpact(
        product_system_identifier="system", reference_flow_identifier="flow",
        functional_unit_quantity=1.0, functional_unit_unit="kg",
        indicators=(
            ImpactIndicator(("test", "first"), 2.0, "kg"),
            ImpactIndicator(("test", "second"), 3.0, "m3"),
        ),
        bw2data_version="4.7", bw2calc_version="2.5.0",
    )
    copy_project = Mock(wraps=lifecycle.shutil.copytree)
    calculate = Mock(return_value=impact)
    monkeypatch.setattr(lifecycle.shutil, "copytree", copy_project)
    monkeypatch.setattr(
        "see_impacts_calculation_service.foreground_calculation.calculate_foreground", calculate
    )
    request_dir = tmp_path / "request"
    result = lifecycle._worker({
        "assembly": asdict(assembly), "project_dir": str(source),
        "request_dir": str(request_dir), "project_name": "synthetic",
        "background_database_name": "background", "biosphere_database_name": "biosphere",
    })
    assert result == impact
    copy_project.assert_called_once_with(source, request_dir / "project")
    calculate.assert_called_once_with(
        assembly, project_dir=request_dir / "project", workspace_dir=request_dir / "brightway",
        project_name="synthetic", background_database_name="background",
        biosphere_database_name="biosphere",
    )
