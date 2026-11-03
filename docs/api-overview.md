# Compute Workflow

The service calculates all configured environmental impact indicators in one request. A CE-RISE
Product System selects the foreground activities, and LCI Dataset records supply their inventory
flows. The bundled BONSAI-EF3.1 project provides background activities, elementary flows, and
characterization factors. The service validates the input records, calculates the inventory
once, and returns all indicators in a validated CE-RISE Integrated LCA object.

## Required Inputs

`POST /compute` accepts a JSON object with these four fields:

| Field | Required content |
| --- | --- |
| `model_versions` | `product_system`, `lci_dataset`, and `integrated_lca` schema versions registered in HEX Core. These are model versions, not versions of the individual records. |
| `product_system` | One Product System record with `product_system_identifier`, `lci_dataset_references`, selected `activity_references`, and `reference_flow_specification`. |
| `lci_datasets` | A non-empty array of LCI Dataset records with the referenced identifiers, activities, and flows. |
| `functional_unit` | `reference_flow_identifier`, positive `quantity`, and `unit` for the requested assessment. |

## Record Relationships

The Product System's dataset references must match exactly one supplied LCI Dataset each;
referenced record versions must also match. Selected activities must exist in those datasets.
The Product System reference flow must be a product flow produced by a selected activity, and
its identifier, declared amount, and unit must match the LCI flow. The functional unit repeats
that flow identifier and unit, while its quantity is the amount to assess.

## Foreground and Background Links

The foreground is the inventory supplied in the LCI Dataset records. The background provides
the external activities and elementary flows referenced by that inventory.

Internal foreground links are resolved from the selected activities and their flows. External
product inputs can identify a background activity with `counterpart_activity_reference` or
`output_of_activity_reference`; external waste treatment uses
`counterpart_activity_reference`. These must resolve to activity codes in the configured
background database. Elementary flows use `flow_object_reference` values that resolve in the
configured biosphere database. The service converts compatible flow units and rejects unresolved
or incompatible links. The bundled BONSAI background is prepared by the image build or local
setup. Activity and elementary-flow identifiers in the input records provide the links to it.

In the bundled project, external activities resolve in `BONSAI` and elementary flows resolve in
`ef31_biosphere`. See [Methods and Background](scope.md) for database contents, characterization
factors, and geographic treatment.

## Send a Request

1. Start the service with `HEX_CORE_BASE_URL` pointing to a reachable HEX Core that has the
   requested Product System, LCI Dataset, and Integrated LCA schemas. See [Deployment](deployment.md).
2. Check `GET /capabilities` for the background and `GET /methods` for the configured indicators.
3. Send the model versions, Product System, LCI Dataset records, and functional unit to `POST /compute`.

The [PV Example](pv-example.md) provides the input records, request commands, and complete
calculated result for a photovoltaic panel.

## Read the Response

A successful response has one `lca_analysis_instances` entry containing all 25
`assessment_results.assessment_indicators` entries.

| Location within the analysis instance | What it records |
| --- | --- |
| `study_metadata.functional_unit_specification` | Reference flow, assessed quantity, and unit. |
| `study_metadata.database_info` | Background database name and available release version. |
| `study_metadata.software_info` and `study_metadata.assessment_toolchain` | Service name/version, calculation timestamp, and Brightway library versions. |
| `assessment_inputs.input_references` | Product System, selected LCI Datasets, and background project and source release. |
| `assessment_results.assessment_indicators[]` | Every environmental indicator's method, available method version and factor-set reference, numeric score, and result unit. |

The [API Reference](api-reference.md#post-compute) shows the full result shape. If the
technosphere is singular, `POST /compute` instead returns `status: "not_calculable"` with a
`SINGULAR_TECHNOSPHERE` diagnostic and identified activity groups. This response has no calculated
indicators. Invalid models or links return `422`; unavailable HEX Core validation
returns `503`.

## Diagnostic Requests

`POST /compute/diagnostics` accepts the same inputs and performs the calculation, but returns
only whether it is calculable or a singularity diagnostic. Use `POST /compute` to obtain the
indicators; a separate diagnostic request is not required before computing results.
