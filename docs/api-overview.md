# Compute Workflow

The service calculates one environmental impact indicator per request. A CE-RISE Product System
selects the foreground activities, CE-RISE LCI Datasets supply their inventory flows, and the
configured Brightway project supplies background activities, biosphere flows, and impact
methods. The service validates the input records, constructs the calculation, and returns a
validated CE-RISE Integrated LCA object. There is no separate mapping document to submit.

## Required Inputs

`POST /compute` accepts a JSON object with these five fields:

| Field | Required content |
| --- | --- |
| `model_versions` | `product_system`, `lci_dataset`, and `integrated_lca` schema versions registered in HEX Core. These are model versions, not versions of the individual records. |
| `product_system` | One Product System record with `product_system_identifier`, `lci_dataset_references`, selected `activity_references`, and `reference_flow_specification`. |
| `lci_datasets` | A non-empty array of LCI Dataset records with the referenced identifiers, activities, and flows. |
| `functional_unit` | `reference_flow_identifier`, positive `quantity`, and `unit` for the requested assessment. |
| `impact_method` | One complete array of strings returned under `methods` by `GET /methods`. |

The Product System's dataset references must match exactly one supplied LCI Dataset each;
referenced record versions must also match. Selected activities must exist in those datasets.
The Product System reference flow must be a product flow produced by a selected activity, and
its identifier, declared amount, and unit must match the LCI flow. The functional unit repeats
that flow identifier and unit, while its quantity is the amount to assess.

Internal foreground links are resolved from the selected activities and their flows. External
product inputs can identify a background activity with `counterpart_activity_reference` or
`output_of_activity_reference`; external waste treatment uses
`counterpart_activity_reference`. These must resolve to activity codes in the configured
background database. Elementary flows use `flow_object_reference` values that resolve in the
configured biosphere database. The service converts compatible flow units and rejects unresolved
or incompatible links. The bundled BONSAI background is prepared by the image build or local
setup; it is not included in the request.

## Send a Request

1. Start the service with `HEX_CORE_BASE_URL` pointing to a reachable HEX Core that has the
   requested Product System, LCI Dataset, and Integrated LCA schemas. See [Deployment](deployment.md).
2. Check `GET /capabilities` for the background and `GET /methods` for an exact method array.
3. Send the Product System, LCI Dataset records, functional unit, and method to `POST /compute`.

From the repository root, the committed PV fixtures can form a complete request. This example
uses `jq`, the bundled BONSAI project, and schema versions that must also be registered in your
HEX Core. If your HEX Core has different published versions, change the three `model_versions`
values accordingly:

```bash
jq -n \
  --slurpfile system tests/fixtures/pv/product-system.json \
  --slurpfile inventory tests/fixtures/pv/lci-dataset.json \
  '{
    model_versions: {
      product_system: "0.0.1",
      lci_dataset: "0.0.1",
      integrated_lca: "0.2.0"
    },
    product_system: $system[0],
    lci_datasets: [$inventory[0]],
    functional_unit: {
      reference_flow_identifier: $system[0].reference_flow_specification.reference_flow_identifier,
      quantity: 1.0,
      unit: $system[0].reference_flow_specification.reference_flow_unit_reference
    },
    impact_method: ["EF v3.1", "climate change", "global warming potential (GWP100)"]
  }' > compute-request.json

curl --fail-with-body --silent --show-error \
  -H 'Content-Type: application/json' \
  --data-binary @compute-request.json \
  http://127.0.0.1:8080/compute
```

For this fixture and bundled background, the climate-change indicator is approximately
`109.927731 kg CO2-Eq` for `1 m^2` of the declared reference flow. The automated test checks
this result and validates both input records and the output against published model schemas.

## Read the Response

A successful response has one `lca_analysis_instances` entry and one
`assessment_results.assessment_indicators` entry. It does not use a `status` wrapper.

| Location within the analysis instance | What it records |
| --- | --- |
| `study_metadata.functional_unit_specification` | Reference flow, assessed quantity, and unit. |
| `study_metadata.database_info` | Background database name and available release version. |
| `study_metadata.software_info` and `study_metadata.assessment_toolchain` | Service name/version, calculation timestamp, and Brightway library versions. |
| `assessment_inputs.input_references` | Product System, selected LCI Datasets, and background project and source release. |
| `assessment_results.assessment_indicators[0]` | Environmental method, available method version and factor-set reference, numeric score, and result unit. |

The [API Reference](api-reference.md#post-compute) shows the full result shape. If the
technosphere is singular, `POST /compute` instead returns `status: "not_calculable"` with a
`SINGULAR_TECHNOSPHERE` diagnostic and any activity groups it can identify, not an Integrated
LCA result or score. Invalid models or links return `422`; unavailable HEX Core validation
returns `503`.

`POST /compute/diagnostics` accepts the same request and performs the calculation, but returns
only whether it is calculable or the singularity diagnostic. It does not return the score or an
Integrated LCA object. `GET /health`, `GET /capabilities`, and `GET /methods` support liveness,
background inspection, and method selection; they do not validate a particular compute request.
