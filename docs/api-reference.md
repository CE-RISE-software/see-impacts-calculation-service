# API Reference

## Base URL

```text
http://127.0.0.1:8081/
```

The deployment examples use port `8081` for the calculator and port `8080` for HEX Core.
Interactive OpenAPI documentation is available at `GET /docs`; the OpenAPI document is
available at `GET /openapi.json`.

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

The response contains `calculation_status: "request_dependent"`, a `background` object with the
project name, databases, method count, and sample method identifiers, and a `brightway` object
with the `bw2data` and `bw2calc` versions. Database names and counts depend on the configured
project. Input validation and calculation checks are performed by the compute endpoints.

## `GET /methods`

Returns the full sorted set of impact-method identifiers registered in the configured
Brightway project. Every compute request applies all of these methods to the same calculated
inventory.

The response contains `project_name`, `method_count`, and `methods`. Each entry in `methods`
is an array of strings. For example, the climate-change indicator uses the registered identifier
`["EF 3.1", "Climate change", "Radiative forcing as Global Warming Potential (GWP100)"]`.
The bundled project supplies 25 fixed EF3.1 method entries.
An unavailable project returns `503 BRIGHTWAY_PROJECT_UNAVAILABLE` with an explanation in
`detail.message`.

## `POST /compute`

This endpoint validates input models through HEX Core, assembles a foreground, solves the
inventory once, and applies every configured impact method. It validates and returns one
Integrated LCA object containing all 25 environmental indicators for the bundled EF3.1 project.

### Required Request Fields

| Field | Type and rule |
| --- | --- |
| `model_versions` | Object with `product_system`, `lci_dataset`, and `integrated_lca` version strings available in HEX Core. |
| `product_system` | One Product System object conforming to the selected version. |
| `lci_datasets` | Non-empty array of LCI Dataset objects conforming to the selected version. |
| `functional_unit` | Object with the Product System's `reference_flow_identifier`, a positive finite `quantity`, and its declared `unit`. |

Additional top-level request fields are rejected. The configured impact methods and factors
are supplied by the service.

The [Compute Workflow](api-overview.md#required-inputs) explains the required links between
the CE-RISE records. The [PV Example](pv-example.md) provides a complete request and its results.

### Response

A successful request returns an Integrated LCA object after HEX Core validates it against the
requested `model_versions.integrated_lca` schema. The complete PV result, including all
25 indicators, is in [`tests/fixtures/pv/integrated-lca.json`](https://codeberg.org/CE-RISE-software/see-impacts-calculation-service/src/branch/main/tests/fixtures/pv/integrated-lca.json).

The response contains one `lca_analysis_instances` entry with these sections:

| Section | Contents |
| --- | --- |
| `study_metadata` | Assessment dimension, functional unit, background database and version, service and Brightway versions, and calculation timestamp. |
| `assessment_inputs.input_references` | Product System and LCI Dataset identifiers and model versions, plus the background project and source-archive identifier. |
| `assessment_results.assessment_indicators` | All 25 calculated indicators, each with its result, unit, method, and factor-set reference. |

Each indicator contains:

| Field | Contents |
| --- | --- |
| `assessment_dimension` | `ENVIRONMENTAL`. |
| `indicator_identifier` and `assessment_method` | Full registered method identifier, with its components separated by ` / `. |
| `indicator_name` | Indicator name from the registered method. |
| `indicator_result.numeric_value` | Calculated value for the requested functional unit. |
| `indicator_result.unit` | Result unit from the method metadata. |
| `method_version` | Method dataset version, when recorded in the project. |
| `calculation_model_or_factor_set_reference` | Brightway factor-set identifier, when recorded in the project. |

The method version comes from registered metadata or an explicit version in the method name.
For the bundled EF3.1 family, a value such as `01.00.000` identifies the individual method
dataset's version. It is separate from the EF3.1 family name and from the CE-RISE schema versions
in `model_versions`.
The factor-set reference identifies the factor dataset within the Brightway project. The
background artifact URI identifies the source archive by its SHA-256 checksum. Fields without
a recorded value are omitted. Results are returned to the caller; foreground data are temporary
and the source background remains unchanged.

### Validation Errors

FastAPI returns `422 Unprocessable Entity` when a required field is absent or has an
incompatible JSON type. HEX Core model failures return `422 MODEL_VALIDATION_FAILED`, with
`detail.field` identifying the input and `detail.results` containing the validation findings.
Inconsistent reference-flow links return `422 CALCULATION_INPUT_INVALID`, with `detail.field`
naming the affected field. Missing input or output schemas, or an unavailable HEX Core, return
`503`. A generated result that fails HEX Core validation returns
`500 OUTPUT_MODEL_VALIDATION_FAILED` and is not returned. Worker startup failures and timeouts
return `503 CALCULATION_WORKER_UNAVAILABLE`. When the configured per-process calculation
capacity is full, the service returns `503 CALCULATION_CAPACITY_EXCEEDED`. A singular calculation
returns `200` with the same `not_calculable` diagnostic shape documented below, without a score.

## `POST /compute/diagnostics`

Accepts the same four-field request as `POST /compute`.
The service validates the CE-RISE inputs through HEX Core, assembles the selected foreground,
links external inputs to the configured background and biosphere databases, and attempts the
calculation in a disposable per-request project. The prepared background is not modified. This
endpoint does not return an impact score or an Integrated LCA result.

For the request in the [PV Example](pv-example.md), a diagnostic call returns:

```json
{
  "status": "calculable",
  "request": {
    "product_system_identifier": "pv-panel",
    "functional_unit": {
      "reference_flow_identifier": "PVPanelManufacturingCNAct_flow0_PhotovoltaicPanelSingleSi",
      "quantity": 1.0,
      "unit": "m^2"
    }
  },
  "diagnostic": null
}
```

When Brightway reports a singular technosphere, the response is `200` with
`status: "not_calculable"`, the same `request` summary, and a `diagnostic` object. Its
`code` is `SINGULAR_TECHNOSPHERE`; `message` explains that no unique solution or score is
available. `components` contains any small groups of involved activities the service can
identify. Each activity has a database, code, and name, and each group has
`reachable_from_request`. The `scope` field describes the diagnostic coverage. `components`
can be empty when the diagnostic cannot isolate small activity groups. `reachable_from_request`
reports graph connectivity to the demand, rather than the cause of the singularity.

A foreground or background linkage failure returns `422 CALCULATION_PRECONDITION_FAILED`;
invalid foreground construction returns `422 FOREGROUND_CONSTRUCTION_FAILED`. Input-model and
HEX Core errors follow the same rules as `POST /compute`.

## Error Responses

Errors use the standard FastAPI `detail` envelope:

- `BRIGHTWAY_PROJECT_UNAVAILABLE` (`503`): the configured background project cannot be opened;
- `MODEL_VALIDATION_FAILED` (`422`): an input does not conform to its declared model version;
- `MODEL_SCHEMA_UNAVAILABLE` (`503`): HEX Core has no JSON Schema for a requested input or output model version;
- `MODEL_VALIDATION_UNAVAILABLE` (`503`): HEX Core cannot complete validation;
- `MODEL_VALIDATION_RESPONSE_INVALID` (`502`): HEX Core returned an incomplete validation report;
- `CALCULATION_INPUT_INVALID` (`422`): the functional unit or reference-flow links are inconsistent;
- `OUTPUT_MODEL_VALIDATION_FAILED` (`500`): the generated Integrated LCA object did not pass
  HEX Core validation and was not returned;
- `FOREGROUND_CONSTRUCTION_FAILED` (`422`): the validated input objects cannot be assembled
  into a foreground calculation;
- `CALCULATION_PRECONDITION_FAILED` (`422`): the calculation cannot start or finish
  for a reason other than a reported singular technosphere;
- `CALCULATION_WORKER_UNAVAILABLE` (`503`): the isolated worker could not start or finish;
- `CALCULATION_CAPACITY_EXCEEDED` (`503`): all configured calculation slots are occupied;
  retry after an active calculation finishes.
