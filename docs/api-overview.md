# API Overview

## Design Goals

The API is designed as a synchronous service interaction for impact assessment:

- callers can determine whether the service and approved background project are available;
- callers submit explicit CE-RISE model versions and assessment inputs;
- validation remains owned by `hex-core-service`;
- results will be returned as a structured `integrated-lca` record with provenance.

The API is intentionally specific to SEE impact assessment. It is not a generic Brightway API
and does not expose database-management operations to callers.

## Current API State

The operational endpoints are:

- `GET /health`
- `GET /capabilities`
- `GET /openapi.json`
- `GET /docs`

`POST /compute` already has a request schema, but it is a reserved endpoint. A valid request
currently receives `501 CALCULATION_NOT_IMPLEMENTED`; no validation call or calculation is
performed.

## Reserved Compute Request

The future computation endpoint uses model versions explicitly so the source contracts are
unambiguous:

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

- `model_versions`: published versions of the CE-RISE Product System, LCI Dataset, and
  Integrated LCA model contracts;
- `product_system`: the product assessment input;
- `lci_datasets`: the supplied inventory datasets used by the product assessment;
- `assessment_context`: calculation choices and contextual information that will be defined by
  the mapping and acceptance fixture.

The schema deliberately does not expose a Brightway activity, database, method, or project as
part of the public contract. Those are service-internal implementation details.

## Future Response

After implementation, a successful response will contain the validated `integrated-lca` result
record, validation reports, and enough calculation provenance to identify the model versions,
background release, methods, and mapping used. The exact result shape must be established from
the versioned CE-RISE models and the acceptance fixture, rather than invented in this service.
