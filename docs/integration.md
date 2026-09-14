# Integration With HEX Core Service

## Intended Relationship

The SEE impacts calculation service complements `hex-core-service`; it does not replace it.

The intended responsibility split is:

- `hex-core-service`: CE-RISE model validation, registry access, and record persistence;
- SEE impacts calculation service: impact-assessment orchestration, Brightway mapping, and
  construction of the resulting `integrated-lca` record.

## Future Validation Flow

Before a calculation can begin, the service will validate the selected input contracts through
HEX Core. The model versions are explicit in the public request so that the calculation is tied
to published versions of:

- [Product System](https://codeberg.org/CE-RISE-models/product-system);
- [LCI Dataset](https://codeberg.org/CE-RISE-models/lci-dataset);
- [Integrated LCA](https://codeberg.org/CE-RISE-models/integrated-lca).

For each model family, the planned validation call is:

```text
POST /models/{model-family}/versions/{version}:validate
```

The input payload and then the constructed result must both be validated through this boundary.
The calculation service must not maintain an independent validator or redefine the CE-RISE
models.

## Authentication Forwarding

The included HEX Core client supports forwarding an incoming bearer token to the delegated
validation call:

```http
Authorization: Bearer <token>
```

This becomes active only when the compute orchestration is implemented. The current
`POST /compute` scaffold returns `501` before any delegated request is made.

## Integration Direction

The primary calculation input is payload submission. A client, engineering application, or
agent assembles the assessment payload and sends it to this service. Record lookup or result
persistence through HEX Core can be added as a secondary integration mechanism once the
calculation result contract and acceptance fixture are established.

## Current Boundary

`HEX_CORE_BASE_URL` and `HTTP_TIMEOUT_SECS` are runtime configuration values today, and the
client implementation is available in the source tree. No outbound request is made by the
current HTTP endpoints. This is intentional: the sequence and payloads for delegated validation
must be derived from the model versions and acceptance fixture, not inferred prematurely.
