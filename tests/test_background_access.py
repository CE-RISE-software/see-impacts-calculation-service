import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _probe(project_dir, project_name, workspace_dir):
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    env.pop("BRIGHTWAY2_DIR", None)
    return subprocess.run(
        [
            sys.executable, "-m", "see_impacts_calculation_service.compatibility",
            "--project-dir", str(project_dir),
            "--project-name", project_name,
            "--workspace-dir", str(workspace_dir),
        ],
        env=env, capture_output=True, text=True,
    )


def test_probe_reads_synthetic_background_data(tmp_path):
    source = tmp_path / "background"
    fixture = Path(__file__).parent / "fixtures" / "brightway_smoke.py"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    env.pop("BRIGHTWAY2_DIR", None)
    subprocess.run(
        [sys.executable, str(fixture), "build", str(tmp_path / "builder"), str(source)],
        env=env, check=True, capture_output=True, text=True,
    )

    result = _probe(source, "synthetic", tmp_path / "workspace")

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert {entry["name"] for entry in report["databases"]} == {"background", "biosphere"}
    assert all(entry["datapackage_resource_count"] > 0 for entry in report["databases"])
    background = next(entry for entry in report["databases"] if entry["name"] == "background")
    assert background["sample_key"] == ["background", "activity-1"]
    assert background["sample_exchange_count"] == 2
    assert report["sample_method"] == ["synthetic", "climate"]
    assert report["sample_method_factor_count"] == 1


def test_probe_reads_supplied_bonsai_when_explicitly_requested(tmp_path):
    source = os.environ.get("SEE_IMPACTS_TEST_BACKGROUND_DIR")
    if not source:
        pytest.skip("Set SEE_IMPACTS_TEST_BACKGROUND_DIR to test the supplied background")

    result = _probe(source, "cerise_bonsai", tmp_path / "workspace")

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert {entry["name"] for entry in report["databases"]} == {
        "bonsai", "bonsai biosphere", "biosphere3"
    }
    assert all(entry["sample_key"] for entry in report["databases"])
    assert all(entry["datapackage_resource_count"] > 0 for entry in report["databases"])
    assert report["method_count"] > 0
    assert report["sample_method_factor_count"] > 0
