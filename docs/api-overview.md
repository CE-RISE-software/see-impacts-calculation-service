# API Overview

## Available Endpoints

Use these endpoints with the running HTTP service:

- `GET /health`
- `GET /capabilities`
- `GET /methods`
- `POST /compute`
- `POST /compute/diagnostics`
- `GET /openapi.json`
- `GET /docs`

`GET /health` is a liveness check. `GET /capabilities` verifies that the configured Brightway
project can be opened and reports its databases and a few method examples. `GET /methods`
returns every registered impact-method identifier for use in compute requests.
`POST /compute` validates CE-RISE inputs, calculates one environmental indicator, and validates
the Integrated LCA result through HEX Core before returning it. `POST /compute/diagnostics`
assembles an in-memory foreground,
and attempts the requested Brightway calculation. A singular technosphere returns identified
small activity groups and whether they are reachable from the request. It never returns an
impact score or Integrated LCA result.

## Compute Request Schema

`POST /compute` publishes this JSON request schema:

```json
{
  "model_versions": {
    "product_system": "<version>",
    "lci_dataset": "<version>",
    "integrated_lca": "<version>"
  },
  "product_system": {
    "product_system_identifier": "system-1",
    "lci_dataset_references": [{
      "lci_dataset_reference_identifier": "dataset-ref-1",
      "lci_dataset_identifier": "dataset-1",
      "lci_dataset_version": "1"
    }],
    "activity_references": [{
      "lci_dataset_reference_identifier": "dataset-ref-1",
      "activity_identifier": "activity-1"
    }],
    "reference_flow_specification": {
      "reference_flow_lci_dataset_reference_identifier": "dataset-ref-1",
      "reference_flow_identifier": "flow-1",
      "reference_flow_numerical_value": 2.0,
      "reference_flow_unit_reference": "kg"
    }
  },
  "lci_datasets": [{
    "lci_dataset_identifier": "dataset-1",
    "lci_dataset_version": "1",
    "activities": [{"activity_identifier": "activity-1"}],
    "flows": [{
      "flow_identifier": "flow-1",
      "flow_kind": "PRODUCT_FLOW",
      "output_of_activity_reference": "activity-1",
      "flow_numerical_value": 2.0,
      "flow_unit_reference": "kg"
    }]
  }],
  "functional_unit": {
    "reference_flow_identifier": "flow-1",
    "quantity": 4.0,
    "unit": "kg"
  },
  "impact_method": ["CML v4.8 2016", "climate change", "global warming potential (GWP100)"]
}
```

The fields have these roles:

- `model_versions.product_system` and `model_versions.lci_dataset`: versions of the input model
  contracts;
- `model_versions.integrated_lca`: version of the result model contract;
- `product_system`: input object conforming to the selected Product System version;
- `lci_datasets`: input object(s) conforming to the selected LCI Dataset version;
- `functional_unit`: requested quantity and unit for the Product System reference flow;
- `impact_method`: components of a registered Brightway method identifier;

The result is an object conforming to the selected Integrated LCA version. Callers choose a
registered impact method, while Brightway activities, databases, and project state remain
internal calculation details. The semantic content of the CE-RISE input objects is used to
construct that internal calculation; no additional mapping object or API resource is required
from callers.

`POST /compute/diagnostics` accepts the same request. It returns `calculable` when the
calculation completes with a finite score internally, but does not publish that score.
`not_calculable` reports a singular matrix and its identified activities. See the
[API Reference](api-reference.md) for response details and limitations.

Both endpoints first validate the Product System and each LCI Dataset through HEX Core, then
assemble and calculate the foreground against the configured background. They return `422`
for nonconforming inputs or unresolved links and `503` when required schemas or validation
are unavailable. Only `/compute` validates and returns an Integrated LCA result. Use
`GET /capabilities` to inspect the background project and `GET /methods` to choose a method;
neither guarantees that a particular request is solvable.
