"""Exercise the HTTP compute route against a disposable Brightway project."""

import asyncio
import json
import sys
from pathlib import Path

import httpx

from foreground_calculation_smoke import sample_inputs
from see_impacts_calculation_service.app import create_app
from see_impacts_calculation_service.config import RuntimeConfig


class StubHexCore:
    def __init__(self):
        self.calls = []

    async def schema_available(self, **kwargs):
        return kwargs["model_family"] in {"product-system", "lci-dataset", "integrated-lca"}

    async def validate(self, **kwargs):
        self.calls.append(kwargs)
        return {"passed": True, "results": [{"kind": "JsonSchema", "passed": True}]}


async def main() -> None:
    source = Path(sys.argv[1])
    workspace = Path(sys.argv[2])
    product_system, dataset = sample_inputs("activity-1")
    validator = StubHexCore()
    app = create_app(
        RuntimeConfig(
            bind_address="127.0.0.1",
            port=8080,
            hex_core_base_url="http://hex-core-service:8080",
            http_timeout_secs=30,
            background_project_dir=source,
            background_project_name="synthetic",
            brightway_workspace_dir=workspace,
            background_database_name="background",
            biosphere_database_name="biosphere",
        ),
        hex_core_client=validator,
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        methods = await client.get("/methods")
        request = {
            "model_versions": {
                "product_system": "0.2.0",
                "lci_dataset": "0.2.0",
                "integrated_lca": "0.2.0",
            },
            "product_system": product_system,
            "lci_datasets": [dataset],
            "functional_unit": {
                "reference_flow_identifier": "product-output",
                "quantity": 4.0,
                "unit": "kg",
            },
            "impact_method": ["synthetic", "climate"],
        }
        response, second_response = await asyncio.gather(
            client.post("/compute", json=request),
            client.post("/compute", json=request),
        )
        validated_output = validator.calls[-1]["payload"]
        invalid_request = {**request, "impact_method": ["missing", "method"]}
        invalid_response = await client.post("/compute", json=invalid_request)
    print(json.dumps({
        "methods_status": methods.status_code,
        "methods": methods.json(),
        "compute_status": response.status_code,
        "second_compute_status": second_response.status_code,
        "result": response.json(),
        "second_result": second_response.json(),
        "invalid_compute_status": invalid_response.status_code,
        "invalid_compute_result": invalid_response.json(),
        "validated_families": [call["model_family"] for call in validator.calls],
        "validated_output": validated_output,
        "remaining_request_projects": sorted(
            path.name for path in (workspace / "requests").iterdir()
        ),
    }))


if __name__ == "__main__":
    asyncio.run(main())
