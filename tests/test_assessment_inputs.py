import copy

import pytest

from see_impacts_calculation_service.assessment_inputs import (
    AssessmentInputError,
    resolve_reference_flow,
)


@pytest.fixture
def inputs():
    product_system = {
        "product_system_identifier": "system-1",
        "lci_dataset_references": [
            {
                "lci_dataset_reference_identifier": "dataset-ref-1",
                "lci_dataset_identifier": "dataset-1",
                "lci_dataset_version": "1",
            }
        ],
        "activity_references": [
            {
                "lci_dataset_reference_identifier": "dataset-ref-1",
                "activity_identifier": "activity-1",
            }
        ],
        "reference_flow_specification": {
            "reference_flow_lci_dataset_reference_identifier": "dataset-ref-1",
            "reference_flow_identifier": "flow-1",
            "reference_flow_numerical_value": 2.0,
            "reference_flow_unit_reference": "kg",
        },
    }
    datasets = [
        {
            "lci_dataset_identifier": "dataset-1",
            "lci_dataset_version": "1",
            "activities": [{"activity_identifier": "activity-1"}],
            "flows": [
                {
                    "flow_identifier": "flow-1",
                    "flow_kind": "PRODUCT_FLOW",
                    "output_of_activity_reference": "activity-1",
                    "flow_numerical_value": 2.0,
                    "flow_unit_reference": "kg",
                }
            ],
        }
    ]
    return product_system, datasets


def resolve(inputs, **overrides):
    product_system, datasets = inputs
    options = {"reference_flow_identifier": "flow-1", "quantity": 4.0, "unit": "kg"}
    options.update(overrides)
    return resolve_reference_flow(product_system, datasets, **options)


def test_resolves_reference_flow_and_scales_demand(inputs):
    result = resolve(inputs)

    assert result.product_system_identifier == "system-1"
    assert result.dataset_identifier == "dataset-1"
    assert result.activity_identifier == "activity-1"
    assert result.demand_scale == 2.0


@pytest.mark.parametrize(
    ("change", "field"),
    [
        (lambda system, datasets: system.update(activity_references=[]), "product_system.activity_references"),
        (lambda system, datasets: datasets[0].update(lci_dataset_version="2"), "lci_datasets"),
        (lambda system, datasets: datasets[0].update(flows=[]), "lci_datasets.flows"),
        (
            lambda system, datasets: datasets[0]["flows"][0].update(flow_kind="ELEMENTARY_FLOW"),
            "lci_datasets.flows.flow_kind",
        ),
        (
            lambda system, datasets: datasets[0]["flows"][0].update(output_of_activity_reference="missing"),
            "product_system.activity_references",
        ),
        (
            lambda system, datasets: datasets[0]["flows"][0].update(flow_unit_reference="g"),
            "lci_datasets.flows.flow_unit_reference",
        ),
    ],
)
def test_rejects_unresolvable_reference_flow(inputs, change, field):
    product_system, datasets = copy.deepcopy(inputs)
    change(product_system, datasets)

    with pytest.raises(AssessmentInputError) as error:
        resolve((product_system, datasets))

    assert error.value.field == field


def test_rejects_functional_unit_on_other_flow(inputs):
    with pytest.raises(AssessmentInputError) as error:
        resolve(inputs, reference_flow_identifier="another-flow")

    assert error.value.field == "functional_unit.reference_flow_identifier"


def test_rejects_functional_unit_with_other_unit(inputs):
    with pytest.raises(AssessmentInputError) as error:
        resolve(inputs, unit="g")

    assert error.value.field == "functional_unit.unit"


def test_rejects_unresolved_nonreference_activity(inputs):
    product_system, datasets = inputs
    product_system["activity_references"].append(
        {
            "lci_dataset_reference_identifier": "dataset-ref-1",
            "activity_identifier": "missing-activity",
        }
    )

    with pytest.raises(AssessmentInputError) as error:
        resolve((product_system, datasets))

    assert error.value.field == "product_system.activity_references[1].activity_identifier"
