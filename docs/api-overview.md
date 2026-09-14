# API Overview

## Available Endpoints

Use these endpoints with the running HTTP service:

- `GET /health`
- `GET /capabilities`
- `GET /openapi.json`
- `GET /docs`

`GET /health` is a liveness check. `GET /capabilities` verifies that the configured Brightway
project can be opened and reports the databases and methods that the service can inspect.

## Compute Request Schema

`POST /compute` publishes this JSON request schema:

```json
{
  "model_versions": {
    "product_system": "<version>",
    "lci_dataset": "<version>",
    "integrated_lca": "<version>"
  },
  "product_system": {},
  "lci_datasets": [],
  "assessment_context": {}
}
```

The fields have these roles:

- `model_versions.product_system` and `model_versions.lci_dataset`: versions of the input model
  contracts;
- `model_versions.integrated_lca`: version of the result model contract;
- `product_system`: input object conforming to the selected Product System version;
- `lci_datasets`: input object(s) conforming to the selected LCI Dataset version;
- `assessment_context`: additional assessment information.

The result belongs in an object conforming to the selected Integrated LCA version. Brightway
activities, databases, methods, and project state are internal calculation details. The semantic
content of the CE-RISE input objects is used to construct that internal calculation; no additional
mapping object, request field, or API resource is required from callers.

The endpoint returns `501 CALCULATION_NOT_IMPLEMENTED`. It has no calculation or validation
side effects. Use `GET /capabilities` to inspect an available Brightway project.
