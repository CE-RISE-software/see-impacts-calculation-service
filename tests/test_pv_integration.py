"""Build the bundled background and calculate the converted PV fixture through HTTP."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import pytest
from jsonschema.validators import validator_for
from packaging.version import Version

from see_impacts_calculation_service.app import create_app
from see_impacts_calculation_service.config import RuntimeConfig


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/pv"
BACKGROUND = ROOT / "data/background"
METHOD = ("EF 3.1", "Climate change", "Radiative forcing as Global Warming Potential (GWP100)")
EXPECTED_SCORE = 145.81751590492595
BACKGROUND_METADATA = json.loads((BACKGROUND / "project.json").read_text())
MODEL_CLASSES = {
    "product-system": "ProductSystem",
    "lci-dataset": "LCIDataset",
    "integrated-lca": "IntegratedLCAResults",
}


class PublishedModelValidator:
    def __init__(self) -> None:
        self.schemas = {}
        self.validators = {}
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            for family, model_class in MODEL_CLASSES.items():
                repository = f"https://codeberg.org/CE-RISE-models/{family}"
                response = client.get(
                    f"https://codeberg.org/api/v1/repos/CE-RISE-models/{family}/tags?limit=50"
                )
                response.raise_for_status()
                versions = [
                    Version(tag["name"][1:])
                    for tag in response.json()
                    if re.fullmatch(r"v\d+\.\d+\.\d+", tag["name"])
                ]
                if not versions:
                    raise RuntimeError(f"No published release tag found for {family}.")
                version = str(max(versions))
                response = client.get(
                    f"{repository}/raw/tag/pages-v{version}/generated/schema.json"
                )
                response.raise_for_status()
                schema = response.json()
                if schema.get("version") != version or model_class not in schema.get("$defs", {}):
                    raise RuntimeError(f"Published {family} schema does not match version {version}.")
                model_schema = {**schema, "$ref": f"#/$defs/{model_class}"}
                validator_class = validator_for(model_schema)
                validator_class.check_schema(model_schema)
                self.schemas[family] = schema
                self.validators[family] = validator_class(model_schema)
        self.validated_families: list[str] = []

    async def schema_available(self, *, model_family: str, model_version: str, **kwargs) -> bool:
        return self.schemas.get(model_family, {}).get("version") == model_version

    async def validate(self, *, model_family: str, payload: dict, **kwargs) -> dict:
        errors = list(self.validators[model_family].iter_errors(payload))
        self.validated_families.append(model_family)
        return {
            "passed": not errors,
            "results": [{
                "kind": "JsonSchema",
                "passed": not errors,
                "violations": [{"path": error.json_path, "message": error.message} for error in errors],
            }],
        }


@pytest.fixture(scope="module")
def published_validator() -> PublishedModelValidator:
    return PublishedModelValidator()


def _run_background_step(*args: str) -> None:
    with TemporaryDirectory(prefix="see-pv-import-home-") as home:
        environment = {
            "HOME": home,
            "XDG_DATA_HOME": str(Path(home) / "data"),
            "XDG_CACHE_HOME": str(Path(home) / "cache"),
            "XDG_CONFIG_HOME": str(Path(home) / "config"),
            "PATH": os.environ.get("PATH", ""),
            "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS", "4"),
        }
        result = subprocess.run(
            [sys.executable, "-m", f"see_impacts_calculation_service.{args[0]}", *args[1:]],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=1800,
        )
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed:\n{result.stdout}\n{result.stderr}")


async def _compute(
    project: Path, workspace: Path, validator: PublishedModelValidator
) -> dict:
    app = create_app(
        RuntimeConfig(
            bind_address="127.0.0.1",
            port=8080,
            hex_core_base_url="http://hex-core-service:8080",
            http_timeout_secs=30,
            background_project_dir=project,
            background_project_name="cerise_bonsai",
            brightway_workspace_dir=workspace,
            background_database_name="BONSAI",
            biosphere_database_name="ef31_biosphere",
        ),
        hex_core_client=validator,
    )
    system = json.loads((FIXTURE / "product-system.json").read_text())
    dataset = json.loads((FIXTURE / "lci-dataset.json").read_text())
    request = {
        "model_versions": {
            "product_system": validator.schemas["product-system"]["version"],
            "lci_dataset": validator.schemas["lci-dataset"]["version"],
            "integrated_lca": validator.schemas["integrated-lca"]["version"],
        },
        "product_system": system,
        "lci_datasets": [dataset],
        "functional_unit": {
            "reference_flow_identifier": system["reference_flow_specification"]["reference_flow_identifier"],
            "quantity": 1.0,
            "unit": "m^2",
        },
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post("/compute", json=request)
    assert response.status_code == 200, response.text
    return response.json()


def test_pv_fixture_with_bundled_background(
    tmp_path: Path, published_validator: PublishedModelValidator
) -> None:
    destination = tmp_path / "projects"
    _run_background_step(
        "prepare_background",
        str(BACKGROUND / "cerise_bonsai.tar.gz"),
        str(destination),
        "--project-name", "cerise_bonsai",
    )
    project = destination / "cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9"
    with (project / "lci" / "databases.db").open("rb") as stream:
        before = hashlib.file_digest(stream, "sha256").hexdigest()

    workspace = tmp_path / "request-workspace"
    result = asyncio.run(_compute(project, workspace, published_validator))
    indicators = result["lca_analysis_instances"][0]["assessment_results"]["assessment_indicators"]
    expected_result = json.loads((FIXTURE / "integrated-lca.json").read_text())
    expected_indicators = expected_result["lca_analysis_instances"][0]["assessment_results"]["assessment_indicators"]
    _assert_complete_indicators(result)
    assert len(indicators) == len(expected_indicators)
    for actual, expected in zip(indicators, expected_indicators, strict=True):
        assert actual["indicator_identifier"] == expected["indicator_identifier"]
        assert actual["indicator_result"]["numeric_value"] == pytest.approx(
            expected["indicator_result"]["numeric_value"], rel=1e-7, abs=1e-12
        )
    indicator = next(item for item in indicators if item["indicator_identifier"] == " / ".join(METHOD))
    assert indicator["indicator_result"]["numeric_value"] == pytest.approx(EXPECTED_SCORE, abs=0.001)
    assert indicator["indicator_result"]["unit"] == "kg CO2-Eq"
    assert indicator["method_version"] == "01.00.000"
    assert indicator["calculation_model_or_factor_set_reference"] == (
        "ef-31cr.54f4488dea758642f545ebdab88aaca5"
    )
    metadata = result["lca_analysis_instances"][0]["study_metadata"]
    assert metadata["database_info"]["database_version"] == BACKGROUND_METADATA["source_version"]
    assert datetime.fromisoformat(metadata["software_info"]["calculation_timestamp"]).tzinfo
    assert result["lca_analysis_instances"][0]["assessment_inputs"]["input_references"][-1][
        "source_artifact_uri"
    ] == BACKGROUND_METADATA["source_artifact_uri"]
    assert published_validator.validated_families == [
        "product-system", "lci-dataset", "integrated-lca"
    ]
    assert list((workspace / "requests").iterdir()) == []
    with (project / "lci" / "databases.db").open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == before


def test_pv_records_against_published_models(
    published_validator: PublishedModelValidator,
) -> None:
    validator = published_validator
    system = json.loads((FIXTURE / "product-system.json").read_text())
    dataset = json.loads((FIXTURE / "lci-dataset.json").read_text())
    result = json.loads((FIXTURE / "integrated-lca.json").read_text())
    _assert_complete_indicators(result)
    records = {
        "product-system": system,
        "lci-dataset": dataset,
        "integrated-lca": result,
    }
    for family, record in records.items():
        assert validator.validators[family].is_valid(record), family

    for family, record in (
        ("product-system", {**system, "activity_references": "invalid"}),
        ("lci-dataset", {**dataset, "flows": "invalid"}),
        ("integrated-lca", {"lca_analysis_instances": "invalid"}),
    ):
        assert not validator.validators[family].is_valid(record), family

    invalid_result = json.loads(json.dumps(result))
    invalid_result["lca_analysis_instances"][0]["assessment_results"]["assessment_indicators"][-1][
        "indicator_result"
    ]["numeric_value"] = "invalid"
    assert not validator.validators["integrated-lca"].is_valid(invalid_result)


def _assert_complete_indicators(result: dict) -> None:
    indicators = result["lca_analysis_instances"][0]["assessment_results"]["assessment_indicators"]
    methods = sorted(BACKGROUND_METADATA["methods"], key=lambda entry: entry["name"])
    assert len(indicators) == len(methods) == 25
    assert len({indicator["indicator_identifier"] for indicator in indicators}) == 25
    for indicator, method in zip(indicators, methods, strict=True):
        assert indicator["assessment_method"] == " / ".join(method["name"])
        assert indicator["indicator_result"]["unit"] == method["unit"]
        assert indicator["method_version"] == method["version"]
        assert indicator["calculation_model_or_factor_set_reference"] == method["factor_set_reference"]
