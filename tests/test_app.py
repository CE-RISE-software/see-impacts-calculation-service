import asyncio

import httpx

from see_impacts_calculation_service.app import create_app
from see_impacts_calculation_service.config import RuntimeConfig


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


def test_compute_is_not_available(tmp_path):
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
    request = {
        "model_versions": {
            "product_system": "0.0.1",
            "lci_dataset": "0.0.1",
            "integrated_lca": "0.0.1",
        },
        "product_system": {},
    }

    response = asyncio.run(_request(app, "POST", "/compute", json=request))

    assert response.status_code == 501
    assert response.json()["detail"]["code"] == "CALCULATION_NOT_IMPLEMENTED"
    assert response.json()["detail"]["message"] == (
        "Impact calculation is not available. Use GET /capabilities to verify "
        "the configured Brightway project."
    )


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
