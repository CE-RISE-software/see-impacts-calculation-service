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
  "calculation_status": "scaffolded",
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
example values reflect the currently approved local project and are not a fixed API guarantee.

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

Reserved calculation endpoint. It accepts a CE-RISE-oriented request shape now so clients and
the implementation can converge on a stable public boundary.

### Request Schema

- `model_versions`
  - type: object
  - required: yes
  - fields: `product_system`, `lci_dataset`, and `integrated_lca`, each a string
- `product_system`
  - type: object
  - required: yes
  - meaning: Product System input following the selected model version
- `lci_datasets`
  - type: array of objects
  - required: no
  - default: `[]`
  - meaning: LCI Dataset inputs following the selected model version
- `assessment_context`
  - type: object
  - required: no
  - default: `{}`
  - meaning: assessment information whose detailed contract will be fixed with the mapping

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

### Current Response

For every request that satisfies the top-level schema, the scaffold returns `501`:

```json
{
  "detail": {
    "code": "CALCULATION_NOT_IMPLEMENTED",
    "message": "The HTTP contract is reserved, but CE-RISE-to-Brightway mapping, HEX Core validation orchestration, and the acceptance fixture are not implemented yet."
  }
}
```

The endpoint currently has no calculation side effects. It does not call HEX Core, create
foreground data, or modify the background project.

### Validation Errors

FastAPI returns `422 Unprocessable Entity` when a required top-level field is absent or has an
incompatible JSON type. Model-level validation will be delegated to HEX Core once the
calculation workflow is implemented.

## Error Responses

Errors use the standard FastAPI `detail` envelope. The currently defined service error codes
are:

- `BRIGHTWAY_PROJECT_UNAVAILABLE` (`503`): the configured background project cannot be opened;
- `CALCULATION_NOT_IMPLEMENTED` (`501`): a syntactically valid compute request was received,
  but the calculation workflow is not available yet.
