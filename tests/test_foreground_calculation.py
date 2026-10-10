import json
import os
import subprocess
import sys
from math import isfinite
from pathlib import Path
from types import SimpleNamespace

import pytest

from see_impacts_calculation_service.foreground_calculation import (
    ForegroundCalculationError,
    _converted_amount,
    _required_database_names,
)


def test_converts_cubic_meter_to_brightway_m3_unit():
    assert _converted_amount(2.0, "m^3", "m3", "water") == 2.0


def test_selects_background_dependencies_but_not_unrelated_databases():
    bd = SimpleNamespace(databases={
        "background": {"depends": ["biosphere"]},
        "biosphere": {},
        "unrelated": {},
    })

    assert _required_database_names(bd, "background", "biosphere") == (
        "background", "biosphere"
    )


def test_rejects_missing_background_dependency():
    bd = SimpleNamespace(databases={"background": {"depends": ["missing"]}, "biosphere": {}})

    with pytest.raises(ForegroundCalculationError, match="unavailable database"):
        _required_database_names(bd, "background", "biosphere")


def test_combines_foreground_background_and_direct_emission(tmp_path):
    fixture_dir = Path(__file__).parent / "fixtures"
    source = tmp_path / "background"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    env.pop("BRIGHTWAY2_DIR", None)
    subprocess.run(
        [sys.executable, str(fixture_dir / "brightway_smoke.py"), "build", str(tmp_path / "builder"), str(source)],
        env=env, check=True, capture_output=True, text=True,
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    env["BRIGHTWAY2_DIR"] = str(workspace)
    result = subprocess.run(
        [sys.executable, str(fixture_dir / "foreground_calculation_smoke.py"),
         str(source), str(workspace), "activity-1"],
        env=env, check=True, capture_output=True, text=True,
    )

    report = json.loads(result.stdout.rsplit("\n", 2)[-2])
    assert report["impact"]["score"] == 54.0
    assert report["impact"]["score_unit"] == "kg CO2-eq"
    assert report["databases"] == ["background", "biosphere"]


def test_rejects_unresolvable_background_identifier(tmp_path):
    fixture_dir = Path(__file__).parent / "fixtures"
    source = tmp_path / "background"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    env.pop("BRIGHTWAY2_DIR", None)
    subprocess.run(
        [sys.executable, str(fixture_dir / "brightway_smoke.py"), "build", str(tmp_path / "builder"), str(source)],
        env=env, check=True, capture_output=True, text=True,
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    env["BRIGHTWAY2_DIR"] = str(workspace)
    result = subprocess.run(
        [sys.executable, str(fixture_dir / "foreground_calculation_smoke.py"),
         str(source), str(workspace), "missing-background"],
        env=env, capture_output=True, text=True,
    )

    assert result.returncode != 0
    assert "missing-background" in result.stderr


def test_converts_foreground_input_to_background_unit(tmp_path):
    fixture_dir = Path(__file__).parent / "fixtures"
    source = tmp_path / "background"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    env.pop("BRIGHTWAY2_DIR", None)
    subprocess.run(
        [sys.executable, str(fixture_dir / "brightway_smoke.py"), "build", str(tmp_path / "builder"), str(source)],
        env=env, check=True, capture_output=True, text=True,
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    env["BRIGHTWAY2_DIR"] = str(workspace)
    result = subprocess.run(
        [sys.executable, str(fixture_dir / "foreground_calculation_smoke.py"),
         str(source), str(workspace), "activity-1", "g", "2000"],
        env=env, check=True, capture_output=True, text=True,
    )

    report = json.loads(result.stdout.rsplit("\n", 2)[-2])
    assert report["impact"]["score"] == 54.0


def test_background_linked_waste_adds_treatment_impact(tmp_path):
    fixture_dir = Path(__file__).parent / "fixtures"
    source = tmp_path / "background"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    env.pop("BRIGHTWAY2_DIR", None)
    subprocess.run(
        [sys.executable, str(fixture_dir / "brightway_smoke.py"), "build", str(tmp_path / "builder"), str(source)],
        env=env, check=True, capture_output=True, text=True,
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    env["BRIGHTWAY2_DIR"] = str(workspace)
    result = subprocess.run(
        [sys.executable, str(fixture_dir / "foreground_calculation_smoke.py"),
         str(source), str(workspace), "activity-1", "kg", "2.0", "0.25"],
        env=env, check=True, capture_output=True, text=True,
    )

    report = json.loads(result.stdout.rsplit("\n", 2)[-2])
    assert report["impact"]["score"] == 60.0


def test_singular_diagnostic_identifies_reachable_and_separate_activities(tmp_path):
    fixture_dir = Path(__file__).parent / "fixtures"
    source = tmp_path / "background"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    env.pop("BRIGHTWAY2_DIR", None)
    subprocess.run(
        [sys.executable, str(fixture_dir / "brightway_smoke.py"), "build-singular", str(tmp_path / "builder"), str(source)],
        env=env, check=True, capture_output=True, text=True,
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    env["BRIGHTWAY2_DIR"] = str(workspace)
    result = subprocess.run(
        [sys.executable, str(fixture_dir / "foreground_calculation_smoke.py"),
         str(source), str(workspace), "activity-1"],
        env=env, check=True, capture_output=True, text=True,
    )

    report = json.loads(result.stdout.rsplit("\n", 2)[-2])
    assert report["status"] == "not_calculable"
    assert "score" not in report
    assert report["diagnostic"]["code"] == "SINGULAR_TECHNOSPHERE"
    components = report["diagnostic"]["components"]
    assert {
        (frozenset(activity["code"] for activity in item["activities"]), item["reachable_from_request"])
        for item in components
    } == {
        (frozenset({"reachable-a", "reachable-b"}), True),
        (frozenset({"separate-a", "separate-b"}), False),
    }


def test_supplied_bonsai_foreground_run_produces_score(tmp_path):
    source = os.environ.get("SEE_IMPACTS_TEST_BACKGROUND_DIR")
    if not source:
        pytest.skip("Set SEE_IMPACTS_TEST_BACKGROUND_DIR to test the supplied background")
    fixture = Path(__file__).parent / "fixtures" / "bonsai_foreground_smoke.py"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    env.pop("BRIGHTWAY2_DIR", None)
    result = subprocess.run(
        [sys.executable, str(fixture), source, str(tmp_path / "workspace")],
        env=env, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["status"] == "calculable"
    assert isfinite(report["impact"]["score"])
    assert report["impact"]["score_unit"]
