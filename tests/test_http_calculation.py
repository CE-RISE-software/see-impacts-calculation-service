import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def test_compute_http_with_real_synthetic_brightway_project(tmp_path):
    fixture_dir = Path(__file__).parent / "fixtures"
    source = tmp_path / "background"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    env.pop("BRIGHTWAY2_DIR", None)
    subprocess.run(
        [
            sys.executable,
            str(fixture_dir / "brightway_smoke.py"),
            "build",
            str(tmp_path / "builder"),
            str(source),
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    background_digest = hashlib.sha256((source / "lci" / "databases.db").read_bytes()).hexdigest()
    env["BRIGHTWAY2_DIR"] = str(workspace)
    result = subprocess.run(
        [sys.executable, str(fixture_dir / "http_calculation_smoke.py"), str(source), str(workspace)],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout.rsplit("\n", 2)[-2])
    assert report["methods_status"] == 200
    assert report["methods"] == {
        "project_name": "synthetic",
        "method_count": 1,
        "methods": [["synthetic", "climate"]],
    }
    assert report["compute_status"] == 200
    assert report["second_compute_status"] == 200
    assert report["result"] == report["validated_output"]
    assert report["second_result"] == report["result"]
    assert report["invalid_compute_status"] == 422
    assert report["invalid_compute_result"]["detail"]["code"] == "CALCULATION_PRECONDITION_FAILED"
    assert report["remaining_request_projects"] == []
    assert hashlib.sha256((source / "lci" / "databases.db").read_bytes()).hexdigest() == background_digest
    instance = report["result"]["lca_analysis_instances"][0]
    indicator = instance["assessment_results"]["assessment_indicators"][0]
    assert indicator["indicator_result"] == {"numeric_value": 54.0, "unit": "kg CO2-eq"}
    tools = instance["study_metadata"]["assessment_toolchain"]["tool_executions"]
    assert [(item["tool_identifier"], item["tool_version"]) for item in tools] == [
        ("bw2data", "4.7"),
        ("bw2calc", "2.5.0"),
    ]
    assert sorted(report["validated_families"]) == sorted(
        ["product-system", "lci-dataset"] * 3 + ["integrated-lca"] * 2
    )
