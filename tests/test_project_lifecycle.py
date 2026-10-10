import asyncio
import logging

import pytest

from see_impacts_calculation_service.assessment_inputs import ReferenceFlowDemand
from see_impacts_calculation_service.foreground import ForegroundAssembly
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
    class FailedProcess:
        def __init__(self):
            self.returncode = returncode

        async def communicate(self, payload):
            return stdout, b"Traceback: worker import failed\n"

    async def start_worker(*args, **kwargs):
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
                method=("example", "method"),
            )
        )

    assert "worker import failed" in caplog.text
    assert "worker import failed" not in str(error.value)
    assert list((tmp_path / "workspace" / "requests").iterdir()) == []
