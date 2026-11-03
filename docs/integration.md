# HEX Core Integration

## Input and Output Models

The service uses these CE-RISE data models:

| Record | Data Model | Validation |
| --- | --- | --- |
| `product_system` | [Product System](https://codeberg.org/CE-RISE-models/product-system) | Before foreground construction. |
| Each entry in `lci_datasets` | [LCI Dataset](https://codeberg.org/CE-RISE-models/lci-dataset) | Before foreground construction. |
| Generated result | [Integrated LCA](https://codeberg.org/CE-RISE-models/integrated-lca) | After calculation, before returning the result. |

`model_versions` specifies the schema versions registered in HEX Core. These are distinct
from the versions assigned to individual input records.

## Validation Requests

Both compute endpoints check the Product System and each LCI Dataset against the versions named
in `model_versions`. After a successful calculation, `POST /compute` also validates its
generated Integrated LCA object against `model_versions.integrated_lca`. For each record, the
service first requests the JSON Schema artifact from HEX Core and then calls:

```text
GET /models/{model-family}/versions/{version}/schema
POST /models/{model-family}/versions/{version}:validate
```

The validation request body is a JSON object whose `payload` field contains the record.

The validation report must include a JSON Schema result for the requested model version.
Failed input validation returns `422` with HEX Core's findings. Failed output validation
returns `500`, and the generated result is not returned. An unavailable schema or HEX Core
returns `503`; a malformed report returns `502`. After input validation, the service checks
reference-flow links and assembles the inventory.

## Connection and Authentication

Set `HEX_CORE_BASE_URL` to the running HEX Core service. If it requires bearer-token
authentication, provide `HEX_CORE_BEARER_TOKEN` through deployment secrets. The token is
sent only to HEX Core and is not included in the health response.

See [Deployment](deployment.md#runtime-configuration) for connection settings and the
[API Reference](api-reference.md#error-responses) for validation error codes.
