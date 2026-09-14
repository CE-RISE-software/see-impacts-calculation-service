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


def test_compute_is_not_enabled_without_mapping_and_fixture(tmp_path):
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
