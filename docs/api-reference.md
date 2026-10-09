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
  "version": "0.0.1",
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
  "calculation_status": "request_dependent",
  "background": {
    "project_name": "cerise_bonsai",
    "databases": [
      {
        "name": "bonsai",
        "backend": "iotable",
        "format": "EXIOBASE 3",
        "activity_count": 42088
      }
    ],
    "method_count": 668,
    "method_examples": [
      ["CML v4.8 2016", "acidification", "acidification (incl. fate, average Europe total, A&B)"],
      ["CML v4.8 2016", "climate change", "global warming potential (GWP100)"],
      ["CML v4.8 2016", "ecotoxicity: freshwater", "freshwater aquatic ecotoxicity (FAETP inf)"],
      ["CML v4.8 2016", "ecotoxicity: marine", "marine aquatic ecotoxicity (MAETP inf)"],
      ["CML v4.8 2016", "ecotoxicity: terrestrial", "terrestrial ecotoxicity (TETP inf)"]
    ]
  },
  "brightway": {
    "bw2data_version": "4.7",
    "bw2calc_version": "2.5.0"
  }
}
```

The database names, counts, and method examples are determined by the configured project. The
example values reflect the approved local project used for this service and are not a fixed API
guarantee. Listing methods does not prove that an LCIA will produce a finite score.

## `GET /methods`

Returns the full sorted set of impact-method identifiers registered in the configured
Brightway project. Pass one `methods` entry unchanged as `impact_method` in a compute request.
This is method discovery, not a guarantee that a particular request can be solved.

```json
{
  "project_name": "cerise_bonsai",
  "method_count": 668,
  "methods": [
    ["CML v4.8 2016", "acidification", "acidification (incl. fate, average Europe total, A&B)"],
    ["CML v4.8 2016", "climate change", "global warming potential (GWP100)"]
  ]
}
```

The list above is abbreviated; the actual response contains all registered methods. An
unavailable project returns `503 BRIGHTWAY_PROJECT_UNAVAILABLE`.

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

This endpoint validates input models through HEX Core, assembles a foreground, calculates one
environmental indicator, then validates and returns an Integrated LCA object. Its calculation
depends on the configured background data, requested method, and resolvable inputs.

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
  - required: yes; at least one object
  - meaning: LCI Dataset input objects following the selected model version
- `functional_unit`
  - type: object
  - required: yes
  - `reference_flow_identifier`: identifier of the Product System reference flow
  - `quantity`: positive finite requested quantity
  - `unit`: unit matching the Product System reference-flow unit
- `impact_method`
  - type: array of strings
  - required: yes; at least one component
  - meaning: registered Brightway impact-method identifier

### Request

```json
{
  "model_versions": {
    "product_system": "<product-system-version>",
    "lci_dataset": "<lci-dataset-version>",
    "integrated_lca": "<integrated-lca-version>"
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

### Response

A successful request returns an Integrated LCA object after HEX Core has validated it against
the requested `model_versions.integrated_lca` schema. The result contains one analysis instance
with the functional unit, input references, and one environmental indicator:

```json
{
  "lca_analysis_instances": [{
    "study_metadata": {
      "assessment_dimensions": ["ENVIRONMENTAL"],
      "database_info": {"background_database": "bonsai"},
      "software_info": {
        "software_name": "see-impacts-calculation-service",
        "software_version": "0.0.1"
      },
      "assessment_toolchain": {
        "tool_executions": [
          {"execution_order": 1, "tool_identifier": "bw2data", "tool_name": "Brightway bw2data", "tool_roles": ["DATA_EXTRACTION"], "tool_version": "4.7"},
          {"execution_order": 2, "tool_identifier": "bw2calc", "tool_name": "Brightway bw2calc", "tool_roles": ["INVENTORY_CALCULATION", "IMPACT_ASSESSMENT"], "tool_version": "2.5.0"}
        ]
      },
      "functional_unit_specification": {
        "reference_flow_identifier": "flow-1",
        "functional_unit_quantity": 4.0,
        "functional_unit_unit": "kg"
      }
    },
    "assessment_inputs": {
      "input_references": [
        {"input_role": "PRODUCT_SYSTEM", "source_model_identifier": "product-system", "source_model_version": "0.2.0", "source_record_identifier": "system-1"},
        {"input_role": "FOREGROUND_INVENTORY", "source_model_identifier": "lci-dataset", "source_model_version": "0.2.0", "source_record_identifier": "dataset-1", "source_record_version": "1"},
        {"input_role": "BACKGROUND_INVENTORY", "source_model_identifier": "brightway-project", "source_record_identifier": "cerise_bonsai"}
      ]
    },
    "assessment_results": {
      "assessment_indicators": [{
        "assessment_dimension": "ENVIRONMENTAL",
        "indicator_identifier": "CML v4.8 2016 / climate change / global warming potential (GWP100)",
        "indicator_name": "global warming potential (GWP100)",
        "assessment_method": "CML v4.8 2016 / climate change / global warming potential (GWP100)",
        "indicator_result": {"numeric_value": 12.5, "unit": "kg CO2-Eq"}
      }]
    }
  }]
}
```

The method identifier is registered in the supplied project, but the score and input objects
are illustrative and do not represent a verified BONSAI result. The project identifier records
which configured background was used; it is not a content checksum or dataset version. The
toolchain versions come from the Brightway runtime used for the calculation. The
endpoint does not write foreground records
or modify the background project. It validates each input model, resolves the reference
flow and foreground links, runs a calculation in memory, and validates the output model.

Apart from the requested impact-method identifier, the schema has no Brightway-specific
fields. Product System and LCI Dataset objects are the
inputs; an Integrated LCA object is the calculation result. The semantic content of the
input objects is used internally to build the Brightway calculation. There is no additional
mapping object to submit or save.

### Validation Errors

FastAPI returns `422 Unprocessable Entity` when a required field is absent or has an
incompatible JSON type. HEX Core model failures return `422 MODEL_VALIDATION_FAILED`, with
`detail.field` identifying the input and `detail.results` containing the validation findings.
Inconsistent reference-flow links return `422 CALCULATION_INPUT_INVALID`, with `detail.field`
naming the affected field. Missing input or output schemas, or an unavailable HEX Core, return
`503`. A generated result that fails HEX Core validation returns
`500 OUTPUT_MODEL_VALIDATION_FAILED` and is not published. A singular calculation returns
`200` with the same `not_calculable` diagnostic shape documented below, without a score.

## `POST /compute/diagnostics`

Accepts the same request as `POST /compute`, including `impact_method`.
The service validates the CE-RISE inputs through HEX Core, assembles the selected foreground,
links external inputs to the configured background and biosphere databases, and attempts the
calculation in memory. The background project is not modified. This endpoint does not return
an impact score or an Integrated LCA result.

When the calculation completes with a finite score internally, the response is:

```json
{
  "status": "calculable",
  "request": {
    "product_system_identifier": "system-1",
    "functional_unit": {
      "reference_flow_identifier": "flow-1",
      "quantity": 4.0,
      "unit": "kg"
    },
    "impact_method": ["CML v4.8 2016", "climate change", "global warming potential (GWP100)"]
  },
  "diagnostic": null
}
```

When Brightway reports a singular technosphere, the response is `200` with
`status: "not_calculable"` and a `SINGULAR_TECHNOSPHERE` diagnostic:

```json
{
  "status": "not_calculable",
  "request": {
    "product_system_identifier": "system-1",
    "functional_unit": {
      "reference_flow_identifier": "flow-1",
      "quantity": 4.0,
      "unit": "kg"
    },
    "impact_method": ["CML v4.8 2016", "climate change", "global warming potential (GWP100)"]
  },
  "diagnostic": {
    "code": "SINGULAR_TECHNOSPHERE",
    "message": "The assembled activity equations do not determine a unique solution; no impact score is available.",
    "components": [{
      "activities": [
        {"database": "bonsai", "code": "activity-a", "name": "Activity A"},
        {"database": "bonsai", "code": "activity-b", "name": "Activity B"}
      ],
      "reachable_from_request": true
    }],
    "scope": "Reports demonstrably singular, aligned activity blocks of 2 to 8 nodes. Reachability traces candidate production and consumption links from the requested demand; it does not establish that foreground detail is missing or that the list is exhaustive."
  }
}
```

The activity list is illustrative. `reachable_from_request` means the component is
structurally reachable through candidate production and consumption links; it does not prove
that the user's foreground is incomplete. Only small, aligned singular blocks are identified,
so an empty `components` array does not mean the matrix is nonsingular. A foreground or
background linkage failure returns `422 CALCULATION_PRECONDITION_FAILED`; invalid foreground
construction returns `422 FOREGROUND_CONSTRUCTION_FAILED`. Input-model and HEX Core errors
follow the same rules as `POST /compute`.

## Error Responses

Errors use the standard FastAPI `detail` envelope. The currently defined service error codes
are:

- `BRIGHTWAY_PROJECT_UNAVAILABLE` (`503`): the configured background project cannot be opened;
- `MODEL_VALIDATION_FAILED` (`422`): an input does not conform to its declared model version;
- `MODEL_SCHEMA_UNAVAILABLE` (`503`): HEX Core has no JSON Schema for a requested input or output model version;
- `MODEL_VALIDATION_UNAVAILABLE` (`503`): HEX Core cannot complete validation;
- `MODEL_VALIDATION_RESPONSE_INVALID` (`502`): HEX Core returned an incomplete validation report;
- `CALCULATION_INPUT_INVALID` (`422`): the functional unit or reference-flow links are inconsistent;
- `OUTPUT_MODEL_VALIDATION_FAILED` (`500`): the generated Integrated LCA object did not pass
  HEX Core validation and was not returned.
- `FOREGROUND_CONSTRUCTION_FAILED` (`422`): the validated input objects cannot be assembled
  into a foreground calculation.
- `CALCULATION_PRECONDITION_FAILED` (`422`): the diagnostic calculation cannot start or finish
  for a reason other than a reported singular technosphere.
