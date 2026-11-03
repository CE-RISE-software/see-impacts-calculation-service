# PV Example

This example calculates the environmental impacts of a photovoltaic panel product system for
`1 m^2` of its declared reference flow. It uses the service's bundled BONSAI background and all
25 configured EF3.1 methods.

## Example Records

The records are included in the repository:

| Record | File | Contents |
| --- | --- | --- |
| Product System | [`product-system.json`](https://codeberg.org/CE-RISE-software/see-impacts-calculation-service/src/branch/main/tests/fixtures/pv/product-system.json) | Selected activities, LCI Dataset reference, and the panel reference flow. |
| LCI Dataset | [`lci-dataset.json`](https://codeberg.org/CE-RISE-software/see-impacts-calculation-service/src/branch/main/tests/fixtures/pv/lci-dataset.json) | The foreground inventory, with 13 activities and 352 flow records. |
| Integrated LCA result | [`integrated-lca.json`](https://codeberg.org/CE-RISE-software/see-impacts-calculation-service/src/branch/main/tests/fixtures/pv/integrated-lca.json) | All 25 calculated indicators and their assessment metadata. |

The example supplies the foreground through the same CE-RISE input records as any other
assessment. Background data, characterization factors, and project preparation are provided
by the service.

## Send the Request

Start the calculator using [Deployment](deployment.md). These commands use its local address,
`http://127.0.0.1:8081`, and require `jq`. The schema versions in the request must be registered
in HEX Core. Run the commands from the repository root:

```bash
jq -n \
  --slurpfile system tests/fixtures/pv/product-system.json \
  --slurpfile inventory tests/fixtures/pv/lci-dataset.json \
  '$system[0].reference_flow_specification as $reference |
  {
    model_versions: {
      product_system: "0.0.1",
      lci_dataset: "0.0.1",
      integrated_lca: "0.2.0"
    },
    product_system: $system[0],
    lci_datasets: [$inventory[0]],
    functional_unit: {
      reference_flow_identifier: $reference.reference_flow_identifier,
      quantity: 1.0,
      unit: $reference.reference_flow_unit_reference
    }
  }' > compute-request.json

curl --fail-with-body --silent --show-error \
  -H 'Content-Type: application/json' \
  --data-binary @compute-request.json \
  --output compute-result.json \
  http://127.0.0.1:8081/compute
```

The response in `compute-result.json` is the complete Integrated LCA object. It contains one
analysis instance and 25 indicators calculated from one inventory.

## Inspect the Results

Count the returned indicators:

```bash
jq '.lca_analysis_instances[0].assessment_results.assessment_indicators | length' \
  compute-result.json
```

The result is `25`. To list each indicator with its value and unit:

```bash
jq -r '.lca_analysis_instances[0].assessment_results.assessment_indicators[] |
  [.indicator_identifier, .indicator_result.numeric_value, .indicator_result.unit] | @tsv' \
  compute-result.json
```

The saved result includes the following values, rounded here for readability. All values refer
to the same `1 m^2` functional unit:

| Indicator | Value | Unit |
| --- | --- | --- |
| Acidification | 1.635790 | `mol H+-Eq` |
| Climate change | 145.817516 | `kg CO2-Eq` |
| Resource use, fossils | 1229.178488 | `MJ` |
| Water use | 272.964862 | `m3 world Eq deprived` |

The [complete result record](https://codeberg.org/CE-RISE-software/see-impacts-calculation-service/src/branch/main/tests/fixtures/pv/integrated-lca.json)
contains every indicator, its method and factor-set reference, the functional unit, input
references, background identification, software versions, and calculation timestamp.

See [Methods and Background](scope.md) for interpretation of categories and subcategories and
[Testing](local-testing.md) for numerical regression and schema-validation checks.
