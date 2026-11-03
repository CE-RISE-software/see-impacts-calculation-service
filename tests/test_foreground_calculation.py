import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from see_impacts_calculation_service.foreground_calculation import (
    ForegroundCalculationError,
    _converted_amount,
    _method_version,
    _required_database_names,
    calculate_foreground,
)


def test_converts_cubic_meter_to_brightway_m3_unit():
    assert _converted_amount(2.0, "m^3", "m3", "water") == 2.0


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("m^2", "m2"),
        ("m^2 * year", "m2*a"),
        ("m2*a", "m^2 * year"),
        ("m^3 * year", "m3*a"),
    ],
)
def test_converts_ef31_area_and_land_occupation_units(source, target):
    assert _converted_amount(2.0, source, target, "land") == 2.0


def test_method_version_uses_metadata_or_explicit_registered_label():
    assert _method_version(("EF v3.1", "climate change"), {}) == "v3.1"
    assert _method_version(("CML v4.8 2016", "climate change"), {}) == "v4.8 2016"
    assert _method_version(("example", "climate change"), {}) is None
    assert _method_version(
        ("EF v3.1", "climate change"), {"version": "release-2"}
    ) == "release-2"


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


@pytest.mark.parametrize(
    ("methods", "message"),
    [
        ({}, "no impact methods"),
        ({("test", "first"): {"unit": "kg"}, ("test", "second"): {}}, "no result unit"),
    ],
)
def test_checks_all_method_metadata_before_calculating(tmp_path, monkeypatch, methods, message):
    monkeypatch.setattr(
        "see_impacts_calculation_service.foreground_calculation._load_brightway_project",
        lambda *args: (SimpleNamespace(methods=methods), None),
    )
    with pytest.raises(ForegroundCalculationError, match=message):
        calculate_foreground(
            SimpleNamespace(),
            project_dir=tmp_path,
            workspace_dir=tmp_path,
            project_name="synthetic",
            background_database_name="background",
            biosphere_database_name="biosphere",
        )


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
    assert report["impact"]["indicators"] == [
        {"method": ["synthetic", "climate"], "score": 54.0, "score_unit": "kg CO2-eq",
         "method_version": None, "factor_set_reference": "syntheticc.3906eb7eec60e14caf0f0e812312b82f"},
        {"method": ["synthetic", "second-indicator"], "score": 90.0, "score_unit": "test-eq",
         "method_version": "2", "factor_set_reference": "synthetics.8ee086df6d32030e7c9e9c3dd398de48"},
    ]
    assert report["inventory_calculations"] == 1
    assert report["linear_solves"] == 1
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
    assert [indicator["score"] for indicator in report["impact"]["indicators"]] == [54.0, 90.0]


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
    assert [indicator["score"] for indicator in report["impact"]["indicators"]] == [60.0, 100.0]


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
