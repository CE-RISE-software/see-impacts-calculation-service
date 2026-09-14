# HEX Core Status

## Available Configuration

The service accepts `HEX_CORE_BASE_URL` and `HTTP_TIMEOUT_SECS` as runtime configuration.
`GET /health` reports the configured HEX Core base URL.

No available HTTP endpoint calls HEX Core. Configuring these values does not enable model
validation through `POST /compute`; that endpoint returns `501 CALCULATION_NOT_IMPLEMENTED`.

## Source-Level Client

`src/see_impacts_calculation_service/hex_core.py` contains `HexCoreClient`, which constructs the
standard validation URL:

```text
POST /models/{model-family}/versions/{version}:validate
```

Its `validate` method accepts a payload and optional bearer token. It is not part of the exposed
HTTP service behavior.

## CE-RISE Data Boundary

The `POST /compute` JSON schema uses the following CE-RISE contracts:

- [Product System](https://codeberg.org/CE-RISE-models/product-system): input object
- [LCI Dataset](https://codeberg.org/CE-RISE-models/lci-dataset): input object(s)
- [Integrated LCA](https://codeberg.org/CE-RISE-models/integrated-lca): result object

Brightway remains inside the calculation service. It is not represented by an additional
CE-RISE model or mapping API. The semantic content of the Product System and LCI Dataset input
objects is used internally to build the Brightway calculation. The service does not validate
these payloads or produce an Integrated LCA record through its available HTTP endpoints.
