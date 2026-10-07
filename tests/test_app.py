import asyncio

import httpx

from see_impacts_calculation_service.app import create_app
from see_impacts_calculation_service.compatibility import BrightwayCompatibilityError
from see_impacts_calculation_service.config import RuntimeConfig
from see_impacts_calculation_service.foreground_calculation import ForegroundCalculationError, ForegroundImpact
from see_impacts_calculation_service.singularity import (
    InvolvedActivity,
    SingularComponent,
    SingularityDiagnostic,
)


class StubHexCore:
    def __init__(self, replies, schema_available=True):
        self.replies = list(replies)
        self.calls = []
        self.schema_exists = schema_available

    async def schema_available(self, **kwargs):
        return self.schema_exists

    async def validate(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


async def _request(app, method, path, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, **kwargs)


def test_health_exposes_service_identity(tmp_path):
    app = create_app(
        RuntimeConfig(
            bind_address="127.0.0.1",
            port=8080,
            hex_core_base_url="http://hex-core-service:8080",
            http_timeout_secs=30,
            background_project_dir=tmp_path / "background",
            background_project_name="cerise_bonsai",
            brightway_workspace_dir=tmp_path / "brightway-workspace",
        )
    )

    response = asyncio.run(_request(app, "GET", "/health"))

    assert response.status_code == 200
    assert response.json()["service"] == "see-impacts-calculation-service"


def test_methods_lists_complete_registered_identifiers(tmp_path, monkeypatch):
    app = _compute_app(tmp_path, StubHexCore([]))
    monkeypatch.setattr(
        "see_impacts_calculation_service.app.list_methods",
        lambda *args: ("synthetic", [["synthetic", "climate"], ["synthetic", "water"]]),
    )

    response = asyncio.run(_request(app, "GET", "/methods"))

    assert response.status_code == 200
    assert response.json() == {
        "project_name": "synthetic",
        "method_count": 2,
        "methods": [["synthetic", "climate"], ["synthetic", "water"]],
    }


def test_methods_reports_unavailable_project(tmp_path, monkeypatch):
    app = _compute_app(tmp_path, StubHexCore([]))

    def unavailable(*args):
        raise BrightwayCompatibilityError("Project unavailable.")

    monkeypatch.setattr("see_impacts_calculation_service.app.list_methods", unavailable)
    response = asyncio.run(_request(app, "GET", "/methods"))

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "BRIGHTWAY_PROJECT_UNAVAILABLE"


def test_compute_reports_calculation_precondition_failure(tmp_path, monkeypatch):
    validator = StubHexCore(
        [{"passed": True, "results": [{"kind": "JsonSchema", "passed": True}]}] * 4
    )
    app = create_app(
        RuntimeConfig(
            bind_address="127.0.0.1",
            port=8080,
            hex_core_base_url="http://hex-core-service:8080",
            http_timeout_secs=30,
            background_project_dir=tmp_path / "background",
            background_project_name="cerise_bonsai",
            brightway_workspace_dir=tmp_path / "brightway-workspace",
            hex_core_bearer_token="service-token",
        ),
        hex_core_client=validator,
    )
    request = {
        "model_versions": {
            "product_system": "0.0.1",
            "lci_dataset": "0.0.1",
            "integrated_lca": "0.0.1",
        },
        "product_system": {
            "product_system_identifier": "system-1",
            "lci_dataset_references": [
                {
                    "lci_dataset_reference_identifier": "dataset-ref-1",
                    "lci_dataset_identifier": "dataset-1",
                    "lci_dataset_version": "1",
                }
            ],
            "activity_references": [
                {
                    "lci_dataset_reference_identifier": "dataset-ref-1",
                    "activity_identifier": "activity-1",
                }
            ],
            "reference_flow_specification": {
                "reference_flow_lci_dataset_reference_identifier": "dataset-ref-1",
                "reference_flow_identifier": "flow-1",
                "reference_flow_numerical_value": 2.0,
                "reference_flow_unit_reference": "kg",
            },
        },
        "lci_datasets": [
            {
                "lci_dataset_identifier": "dataset-1",
                "lci_dataset_version": "1",
                "activities": [{"activity_identifier": "activity-1"}],
                "flows": [
                    {
                        "flow_identifier": "flow-1",
                        "flow_kind": "PRODUCT_FLOW",
                        "output_of_activity_reference": "activity-1",
                        "flow_numerical_value": 2.0,
                        "flow_unit_reference": "kg",
                    }
                ],
            }
        ],
        "functional_unit": {
            "reference_flow_identifier": "flow-1",
            "quantity": 4.0,
            "unit": "kg",
        },
        "impact_method": ["example", "method"],
    }
    def fail_calculation(*args, **kwargs):
        raise ForegroundCalculationError("Unavailable method.")

    monkeypatch.setattr("see_impacts_calculation_service.app.calculate_foreground", fail_calculation)

    response = asyncio.run(_request(app, "POST", "/compute", json=request))

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CALCULATION_PRECONDITION_FAILED"
    assert [(call["model_family"], call["model_version"]) for call in validator.calls] == [
        ("product-system", "0.0.1"),
        ("lci-dataset", "0.0.1"),
    ]
    assert all(call["bearer_token"] == "service-token" for call in validator.calls)

    request["functional_unit"]["reference_flow_identifier"] = "missing"
    invalid_response = asyncio.run(_request(app, "POST", "/compute", json=request))
    assert invalid_response.status_code == 422
    assert invalid_response.json()["detail"]["code"] == "CALCULATION_INPUT_INVALID"


def test_compute_reports_model_validation_failure(tmp_path):
    validator = StubHexCore(
        [
            {"passed": True, "results": [{"kind": "JsonSchema", "passed": True}]},
            {"passed": False, "results": [{"kind": "JsonSchema", "passed": False, "violations": []}]},
        ]
    )
    app = create_app(
        RuntimeConfig(
            bind_address="127.0.0.1",
            port=8080,
            hex_core_base_url="http://hex-core-service:8080",
            http_timeout_secs=30,
            background_project_dir=tmp_path / "background",
            background_project_name="cerise_bonsai",
            brightway_workspace_dir=tmp_path / "brightway-workspace",
        ),
        hex_core_client=validator,
    )
    response = asyncio.run(
        _request(
            app,
            "POST",
            "/compute",
            json={
                "model_versions": {
                    "product_system": "0.0.1",
                    "lci_dataset": "0.0.1",
                    "integrated_lca": "0.0.1",
                },
                "product_system": {},
                "lci_datasets": [{}],
                "functional_unit": {
                    "reference_flow_identifier": "flow-1",
                    "quantity": 1,
                    "unit": "kg",
                },
                "impact_method": ["example", "method"],
            },
        )
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "MODEL_VALIDATION_FAILED"
    assert response.json()["detail"]["field"] == "lci_datasets[0]"
    assert response.json()["detail"]["results"] == [
        {"kind": "JsonSchema", "passed": False, "violations": []}
    ]


def test_compute_reports_hex_core_unavailable(tmp_path):
    validator = StubHexCore([httpx.ConnectError("offline")])
    app = create_app(
        RuntimeConfig(
            bind_address="127.0.0.1",
            port=8080,
            hex_core_base_url="http://hex-core-service:8080",
            http_timeout_secs=30,
            background_project_dir=tmp_path / "background",
            background_project_name="cerise_bonsai",
            brightway_workspace_dir=tmp_path / "brightway-workspace",
        ),
        hex_core_client=validator,
    )
    response = asyncio.run(
        _request(
            app,
            "POST",
            "/compute",
            json={
                "model_versions": {
                    "product_system": "0.0.1",
                    "lci_dataset": "0.0.1",
                    "integrated_lca": "0.0.1",
                },
                "product_system": {},
                "lci_datasets": [{}],
                "functional_unit": {
                    "reference_flow_identifier": "flow-1",
                    "quantity": 1,
                    "unit": "kg",
                },
                "impact_method": ["example", "method"],
            },
        )
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MODEL_VALIDATION_UNAVAILABLE"
    assert response.json()["detail"]["field"] == "product_system"


def test_compute_rejects_missing_hex_schema(tmp_path):
    validator = StubHexCore([], schema_available=False)
    app = create_app(
        RuntimeConfig(
            bind_address="127.0.0.1",
            port=8080,
            hex_core_base_url="http://hex-core-service:8080",
            http_timeout_secs=30,
            background_project_dir=tmp_path / "background",
            background_project_name="cerise_bonsai",
            brightway_workspace_dir=tmp_path / "brightway-workspace",
        ),
        hex_core_client=validator,
    )
    response = asyncio.run(
        _request(
            app,
            "POST",
            "/compute",
            json={
                "model_versions": {
                    "product_system": "0.0.1",
                    "lci_dataset": "0.0.1",
                    "integrated_lca": "0.0.1",
                },
                "product_system": {},
                "lci_datasets": [{}],
                "functional_unit": {
                    "reference_flow_identifier": "flow-1",
                    "quantity": 1,
                    "unit": "kg",
                },
                "impact_method": ["example", "method"],
            },
        )
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MODEL_SCHEMA_UNAVAILABLE"
    assert validator.calls == []


def test_compute_schema_declares_input_and_result_model_versions(tmp_path):
    app = create_app(
        RuntimeConfig(
            bind_address="127.0.0.1",
            port=8080,
            hex_core_base_url="http://hex-core-service:8080",
            http_timeout_secs=30,
            background_project_dir=tmp_path / "background",
            background_project_name="cerise_bonsai",
            brightway_workspace_dir=tmp_path / "brightway-workspace",
        )
    )

    properties = app.openapi()["components"]["schemas"]["ModelVersions"]["properties"]

    assert properties["product_system"]["description"] == (
        "Version of the input product-system model."
    )
    assert properties["lci_dataset"]["description"] == (
        "Version of the input lci-dataset model."
    )
    assert properties["integrated_lca"]["description"] == (
        "Version of the output integrated-lca model."
    )


def test_compute_requires_a_functional_unit(tmp_path):
    app = create_app(
        RuntimeConfig(
            bind_address="127.0.0.1",
            port=8080,
            hex_core_base_url="http://hex-core-service:8080",
            http_timeout_secs=30,
            background_project_dir=tmp_path / "background",
            background_project_name="cerise_bonsai",
            brightway_workspace_dir=tmp_path / "brightway-workspace",
        )
    )

    response = asyncio.run(
        _request(
            app,
            "POST",
            "/compute",
            json={
                "model_versions": {
                    "product_system": "0.0.1",
                    "lci_dataset": "0.0.1",
                    "integrated_lca": "0.0.1",
                },
                "product_system": {},
                "lci_datasets": [{}],
            },
        )
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "functional_unit"]


def test_compute_endpoints_reject_unused_assessment_context(tmp_path):
    validator = StubHexCore([])
    app = _compute_app(tmp_path, validator)
    request = _diagnostic_request()
    request["assessment_context"] = {"scenario": "consumer-owned"}

    for path in ("/compute", "/compute/diagnostics"):
        response = asyncio.run(_request(app, "POST", path, json=request))
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "assessment_context"]
    assert validator.calls == []


def _diagnostic_request():
    return {
        "model_versions": {
            "product_system": "0.0.1",
            "lci_dataset": "0.0.1",
            "integrated_lca": "0.0.1",
        },
        "product_system": {
            "product_system_identifier": "system-1",
            "lci_dataset_references": [{
                "lci_dataset_reference_identifier": "dataset-ref-1",
                "lci_dataset_identifier": "dataset-1",
                "lci_dataset_version": "1",
            }],
            "activity_references": [{
                "lci_dataset_reference_identifier": "dataset-ref-1",
                "activity_identifier": "activity-1",
            }],
            "reference_flow_specification": {
                "reference_flow_lci_dataset_reference_identifier": "dataset-ref-1",
                "reference_flow_identifier": "flow-1",
                "reference_flow_numerical_value": 2.0,
                "reference_flow_unit_reference": "kg",
            },
        },
        "lci_datasets": [{
            "lci_dataset_identifier": "dataset-1",
            "lci_dataset_version": "1",
            "activities": [{"activity_identifier": "activity-1"}],
            "flows": [{
                "flow_identifier": "flow-1",
                "flow_kind": "PRODUCT_FLOW",
                "output_of_activity_reference": "activity-1",
                "flow_numerical_value": 2.0,
                "flow_unit_reference": "kg",
            }],
        }],
        "functional_unit": {
            "reference_flow_identifier": "flow-1",
            "quantity": 4.0,
            "unit": "kg",
        },
        "impact_method": ["example", "method"],
    }


def _calculated_impact():
    return ForegroundImpact(
        product_system_identifier="system-1",
        reference_flow_identifier="flow-1",
        functional_unit_quantity=4.0,
        functional_unit_unit="kg",
        method=("example", "method"),
        score=12.5,
        score_unit="kg CO2-eq",
        bw2data_version="4.7",
        bw2calc_version="2.5.0",
    )


def _compute_app(tmp_path, validator):
    return create_app(
        RuntimeConfig(
            bind_address="127.0.0.1",
            port=8080,
            hex_core_base_url="http://hex-core-service:8080",
            http_timeout_secs=30,
            background_project_dir=tmp_path / "background",
            background_project_name="cerise_bonsai",
            brightway_workspace_dir=tmp_path / "brightway-workspace",
        ),
        hex_core_client=validator,
    )


def test_compute_returns_hex_core_validated_integrated_lca(tmp_path, monkeypatch):
    passed = {"passed": True, "results": [{"kind": "JsonSchema", "passed": True}]}
    validator = StubHexCore([passed] * 3)
    app = _compute_app(tmp_path, validator)
    monkeypatch.setattr(
        "see_impacts_calculation_service.app.calculate_foreground",
        lambda *args, **kwargs: _calculated_impact(),
    )

    response = asyncio.run(_request(app, "POST", "/compute", json=_diagnostic_request()))

    assert response.status_code == 200
    result = response.json()
    instance = result["lca_analysis_instances"][0]
    assert instance["study_metadata"]["functional_unit_specification"] == {
        "reference_flow_identifier": "flow-1",
        "functional_unit_quantity": 4.0,
        "functional_unit_unit": "kg",
    }
    assert instance["assessment_results"]["assessment_indicators"][0] == {
        "assessment_dimension": "ENVIRONMENTAL",
        "indicator_identifier": "example / method",
        "indicator_name": "method",
        "assessment_method": "example / method",
        "indicator_result": {"numeric_value": 12.5, "unit": "kg CO2-eq"},
    }
    assert len(instance["assessment_inputs"]["input_references"]) == 3
    assert instance["assessment_inputs"]["input_references"][-1] == {
        "input_role": "BACKGROUND_INVENTORY",
        "source_model_identifier": "brightway-project",
        "source_record_identifier": "cerise_bonsai",
    }
    assert instance["study_metadata"]["software_info"]["software_version"] == "0.0.1"
    assert [
        (item["tool_identifier"], item["tool_version"])
        for item in instance["study_metadata"]["assessment_toolchain"]["tool_executions"]
    ] == [("bw2data", "4.7"), ("bw2calc", "2.5.0")]
    assert [(call["model_family"], call["model_version"]) for call in validator.calls] == [
        ("product-system", "0.0.1"),
        ("lci-dataset", "0.0.1"),
        ("integrated-lca", "0.0.1"),
    ]
    assert validator.calls[-1]["payload"] == result


def test_compute_rejects_invalid_integrated_lca_output(tmp_path, monkeypatch):
    passed = {"passed": True, "results": [{"kind": "JsonSchema", "passed": True}]}
    failed = {"passed": False, "results": [{"kind": "JsonSchema", "passed": False, "violations": []}]}
    validator = StubHexCore([passed, passed, failed])
    app = _compute_app(tmp_path, validator)
    monkeypatch.setattr(
        "see_impacts_calculation_service.app.calculate_foreground",
        lambda *args, **kwargs: _calculated_impact(),
    )

    response = asyncio.run(_request(app, "POST", "/compute", json=_diagnostic_request()))

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "OUTPUT_MODEL_VALIDATION_FAILED"
    assert response.json()["detail"]["field"] == "integrated_lca"
    assert "lca_analysis_instances" not in response.json()


def test_compute_requires_integrated_lca_schema(tmp_path, monkeypatch):
    passed = {"passed": True, "results": [{"kind": "JsonSchema", "passed": True}]}
    validator = StubHexCore([passed, passed])
    app = _compute_app(tmp_path, validator)
    monkeypatch.setattr(
        "see_impacts_calculation_service.app.calculate_foreground",
        lambda *args, **kwargs: _calculated_impact(),
    )
    original_schema_available = validator.schema_available

    async def schema_available(**kwargs):
        if kwargs["model_family"] == "integrated-lca":
            return False
        return await original_schema_available(**kwargs)

    validator.schema_available = schema_available
    response = asyncio.run(_request(app, "POST", "/compute", json=_diagnostic_request()))

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MODEL_SCHEMA_UNAVAILABLE"
    assert response.json()["detail"]["field"] == "integrated_lca"
    assert len(validator.calls) == 2


def test_compute_returns_singularity_without_output_validation(tmp_path, monkeypatch):
    passed = {"passed": True, "results": [{"kind": "JsonSchema", "passed": True}]}
    validator = StubHexCore([passed, passed])
    app = _compute_app(tmp_path, validator)
    diagnostic = SingularityDiagnostic(
        code="SINGULAR_TECHNOSPHERE",
        message="No unique solution is available.",
        components=(),
        scope="Small singular components were not identified.",
    )

    def fail_calculation(*args, **kwargs):
        raise ForegroundCalculationError("singular", diagnostic=diagnostic)

    monkeypatch.setattr("see_impacts_calculation_service.app.calculate_foreground", fail_calculation)
    response = asyncio.run(_request(app, "POST", "/compute", json=_diagnostic_request()))

    assert response.status_code == 200
    assert response.json()["status"] == "not_calculable"
    assert response.json()["diagnostic"]["code"] == "SINGULAR_TECHNOSPHERE"
    assert len(validator.calls) == 2


def test_compute_diagnostics_reports_singular_activities(tmp_path, monkeypatch):
    validator = StubHexCore(
        [{"passed": True, "results": [{"kind": "JsonSchema", "passed": True}]}] * 2
    )
    app = create_app(
        RuntimeConfig(
            bind_address="127.0.0.1",
            port=8080,
            hex_core_base_url="http://hex-core-service:8080",
            http_timeout_secs=30,
            background_project_dir=tmp_path / "background",
            background_project_name="cerise_bonsai",
            brightway_workspace_dir=tmp_path / "brightway-workspace",
        ),
        hex_core_client=validator,
    )
    diagnostic = SingularityDiagnostic(
        code="SINGULAR_TECHNOSPHERE",
        message="No unique solution is available.",
        components=(SingularComponent(
            activities=(
                InvolvedActivity("bonsai", "activity-a", "Activity A"),
                InvolvedActivity("bonsai", "activity-b", "Activity B"),
            ),
            reachable_from_request=True,
        ),),
        scope="This finding does not establish missing foreground detail.",
    )

    def fail_calculation(*args, **kwargs):
        assert kwargs["method"] == ("example", "method")
        raise ForegroundCalculationError("singular", diagnostic=diagnostic)

    monkeypatch.setattr("see_impacts_calculation_service.app.calculate_foreground", fail_calculation)
    response = asyncio.run(_request(app, "POST", "/compute/diagnostics", json=_diagnostic_request()))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_calculable"
    assert body["request"]["product_system_identifier"] == "system-1"
    assert body["request"]["functional_unit"]["quantity"] == 4.0
    assert body["diagnostic"]["code"] == "SINGULAR_TECHNOSPHERE"
    assert body["diagnostic"]["components"][0]["activities"][0]["code"] == "activity-a"
    assert body["diagnostic"]["components"][0]["reachable_from_request"] is True
    assert "score" not in body
    assert len(validator.calls) == 2


def test_compute_diagnostics_reports_calculable_without_score(tmp_path, monkeypatch):
    validator = StubHexCore(
        [{"passed": True, "results": [{"kind": "JsonSchema", "passed": True}]}] * 2
    )
    app = create_app(
        RuntimeConfig(
            bind_address="127.0.0.1",
            port=8080,
            hex_core_base_url="http://hex-core-service:8080",
            http_timeout_secs=30,
            background_project_dir=tmp_path / "background",
            background_project_name="cerise_bonsai",
            brightway_workspace_dir=tmp_path / "brightway-workspace",
        ),
        hex_core_client=validator,
    )
    monkeypatch.setattr("see_impacts_calculation_service.app.calculate_foreground", lambda *args, **kwargs: None)

    response = asyncio.run(_request(app, "POST", "/compute/diagnostics", json=_diagnostic_request()))

    assert response.status_code == 200
    assert response.json()["status"] == "calculable"
    assert response.json()["diagnostic"] is None
    assert "score" not in response.json()
