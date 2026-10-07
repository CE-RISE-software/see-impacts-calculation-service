import asyncio

import httpx

from see_impacts_calculation_service.hex_core import HexCoreClient


def test_hex_core_client_fetches_schema_and_validates_payload():
    requests = []

    def respond(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, text='{"type":"object"}')
        return httpx.Response(
            200,
            json={"passed": True, "results": [{"kind": "JsonSchema", "passed": True}]},
        )

    client = HexCoreClient(
        "http://hex-core.test/", 5, transport=httpx.MockTransport(respond)
    )

    async def exercise():
        assert await client.schema_available(
            model_family="product-system", model_version="0.0.1", bearer_token="secret"
        )
        return await client.validate(
            model_family="product-system",
            model_version="0.0.1",
            payload={"product_system_identifier": "system-1"},
            bearer_token="secret",
        )

    report = asyncio.run(exercise())

    assert report["passed"] is True
    assert [request.method for request in requests] == ["GET", "POST"]
    assert requests[0].url.path == "/models/product-system/versions/0.0.1/schema"
    assert requests[1].url.path == "/models/product-system/versions/0.0.1:validate"
    assert all(request.headers["authorization"] == "Bearer secret" for request in requests)
    assert requests[1].content == b'{"payload":{"product_system_identifier":"system-1"}}'
