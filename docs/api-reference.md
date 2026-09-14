# API Reference

## Base URL

```text
http://<host>:8080/
```

Interactive OpenAPI documentation is available at `GET /docs`. The machine-readable OpenAPI
document is available at `GET /openapi.json`.

## `GET /health`

Returns service identity and the configured HEX Core and background-project locations. It does
not open the Brightway project, so it can be used as a lightweight liveness check.

Example response:

```json
{
  "status": "ok",
  "service": "see-impacts-calculation-service",
  "version": "0.1.0",
  "hex_core_base_url": "http://127.0.0.1:8080",
  "background_project_dir": "/app/data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9"
}
```

## `GET /capabilities`

Opens the configured Brightway background project and reports the databases and impact methods
that are available to the service. Use this endpoint as a readiness check after provisioning or
updating background data.

Example response shape:

```json
{
  "calculation_status": "not_available",
  "background": {
    "project_name": "cerise_bonsai",
    "databases": [
      {
        "name": "bonsai",
        "backend": "sqlite",
        "format": null,
        "activity_count": 42088
      }
    ],
    "method_count": 668,
    "method_examples": []
  },
  "brightway": {
    "bw2data_version": "3.6.6",
    "bw2calc_version": "1.8.2"
  }
}
```

The database names, counts, and method examples are determined by the mounted project. The
example values reflect the approved local project used for this service and are not a fixed API
guarantee.

If the project cannot be opened, the endpoint returns `503`:

```json
{
  "detail": {
    "code": "BRIGHTWAY_PROJECT_UNAVAILABLE",
    "message": "Brightway project directory does not exist: /configured/path"
  }
}
```

## `POST /compute`

This endpoint exposes the CE-RISE-oriented request schema below. It does not provide an impact
calculation operation.

### Request Schema

- `model_versions`
  - type: object
  - required: yes
  - `product_system`: version of the Product System input model
  - `lci_dataset`: version of the LCI Dataset input model
  - `integrated_lca`: version of the Integrated LCA result model
- `product_system`
  - type: object
  - required: yes
  - meaning: Product System input object following the selected model version
- `lci_datasets`
  - type: array of objects
  - required: no
  - default: `[]`
  - meaning: LCI Dataset input objects following the selected model version
- `assessment_context`
  - type: object
  - required: no
  - default: `{}`
  - meaning: additional assessment information

### Request

```json
{
  "model_versions": {
    "product_system": "<product-system-version>",
    "lci_dataset": "<lci-dataset-version>",
    "integrated_lca": "<integrated-lca-version>"
  },
  "product_system": {},
  "lci_datasets": [],
  "assessment_context": {}
}
```

### Response

Every request that satisfies the top-level schema returns `501`:

```json
{
  "detail": {
    "code": "CALCULATION_NOT_IMPLEMENTED",
    "message": "Impact calculation is not available. Use GET /capabilities to verify the configured Brightway project."
  }
}
```

The endpoint has no calculation side effects. It does not call HEX Core, create
foreground data, or modify the background project.

The schema has no Brightway-specific fields. Product System and LCI Dataset objects are the
inputs; an Integrated LCA object is the calculation result contract. The semantic content of the
input objects is used internally to build the Brightway calculation. There is no additional
mapping object to submit or save.

### Validation Errors

FastAPI returns `422 Unprocessable Entity` when a required top-level field is absent or has an
incompatible JSON type.

## Error Responses

Errors use the standard FastAPI `detail` envelope. The currently defined service error codes
are:

- `BRIGHTWAY_PROJECT_UNAVAILABLE` (`503`): the configured background project cannot be opened;
- `CALCULATION_NOT_IMPLEMENTED` (`501`): a syntactically valid compute request was received,
  but impact calculation is not available.
