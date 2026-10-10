import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from see_impacts_calculation_service.foreground import (
    ForegroundConstructionError,
    assemble_foreground,
)


def example():
    system = {
        "product_system_identifier": "system",
        "lci_dataset_references": [
            {"lci_dataset_reference_identifier": "inventory", "lci_dataset_identifier": "dataset", "lci_dataset_version": "1"}
        ],
        "activity_references": [
            {"lci_dataset_reference_identifier": "inventory", "activity_identifier": "material-production"},
            {"lci_dataset_reference_identifier": "inventory", "activity_identifier": "assembly"},
        ],
        "reference_flow_specification": {
            "reference_flow_lci_dataset_reference_identifier": "inventory",
            "reference_flow_identifier": "finished-output",
            "reference_flow_numerical_value": 2.0,
            "reference_flow_unit_reference": "kg",
        },
    }
    dataset = {
        "lci_dataset_identifier": "dataset",
        "lci_dataset_version": "1",
        "activities": [
            {"activity_identifier": "material-production", "activity_name": "Make material"},
            {"activity_identifier": "assembly", "activity_name": "Assemble product"},
        ],
        "flows": [
            {"flow_identifier": "material-output", "flow_kind": "PRODUCT_FLOW", "flow_direction": "OUTPUT",
             "output_of_activity_reference": "material-production", "flow_object_reference": "material",
             "flow_numerical_value": 3.0, "flow_unit_reference": "kg"},
            {"flow_identifier": "material-input", "flow_kind": "PRODUCT_FLOW", "flow_direction": "INPUT",
             "input_to_activity_reference": "assembly", "counterpart_activity_reference": "material-production",
             "flow_object_reference": "material", "flow_numerical_value": 1.0, "flow_unit_reference": "kg"},
            {"flow_identifier": "finished-output", "flow_kind": "PRODUCT_FLOW", "flow_direction": "OUTPUT",
             "output_of_activity_reference": "assembly", "flow_object_reference": "product",
             "flow_numerical_value": 2.0, "flow_unit_reference": "kg"},
            {"flow_identifier": "electricity-input", "flow_kind": "PRODUCT_FLOW", "flow_direction": "INPUT",
             "input_to_activity_reference": "assembly", "counterpart_activity_reference": "M_electricity|DE",
             "flow_object_reference": "electricity", "flow_numerical_value": 5.0, "flow_unit_reference": "kWh"},
            {"flow_identifier": "co2-output", "flow_kind": "ELEMENTARY_FLOW", "flow_direction": "OUTPUT",
             "output_of_activity_reference": "assembly", "flow_object_reference": "carbon-dioxide",
             "flow_numerical_value": 0.5, "flow_unit_reference": "kg"},
        ],
    }
    return system, dataset


def build(system, dataset):
    return assemble_foreground(
        system, [dataset], reference_flow_identifier="finished-output", quantity=4.0, unit="kg"
    )


def test_assembles_foreground_and_preserves_unresolved_boundaries():
    system, dataset = example()

    result = build(system, dataset)

    assert len(result.activities) == 2
    assert len(result.outputs) == 2
    assert result.reference_output == ("inventory", "finished-output")
    assert result.demand.demand_scale == 2.0
    assert result.inputs[0].provider_output == ("inventory", "material-output")
    assert result.external_inputs[0].counterpart_reference == "M_electricity|DE"
    assert result.elementary_flows[0].direction == "OUTPUT"


def test_rejects_mismatched_internal_unit():
    system, dataset = example()
    dataset["flows"][1]["flow_unit_reference"] = "g"

    with pytest.raises(ForegroundConstructionError, match="output and unit"):
        build(system, dataset)


def test_does_not_guess_provider_from_unit_alone():
    system, dataset = example()
    dataset["flows"][1].pop("counterpart_activity_reference")
    dataset["flows"][1].pop("flow_object_reference")

    result = build(system, dataset)

    assert not result.inputs
    assert {item.key[1] for item in result.external_inputs} == {"material-input", "electricity-input"}


def test_rejects_ambiguous_matching_output():
    system, dataset = example()
    dataset["activities"].append({"activity_identifier": "other-production"})
    system["activity_references"].append(
        {"lci_dataset_reference_identifier": "inventory", "activity_identifier": "other-production"}
    )
    dataset["flows"].append({
        "flow_identifier": "other-material", "flow_kind": "PRODUCT_FLOW",
        "output_of_activity_reference": "other-production", "flow_object_reference": "material",
        "flow_numerical_value": 1.0, "flow_unit_reference": "kg",
    })
    dataset["flows"][1].pop("counterpart_activity_reference")

    with pytest.raises(ForegroundConstructionError, match="multiple foreground outputs"):
        build(system, dataset)


def test_preserves_unselected_producer_as_external_reference():
    system, dataset = example()
    dataset["flows"][3].pop("counterpart_activity_reference")
    dataset["flows"][3]["output_of_activity_reference"] = "grid-activity"

    result = build(system, dataset)

    assert result.external_inputs[0].counterpart_reference == "grid-activity"


def test_background_linked_waste_output_is_treatment_demand():
    system, dataset = example()
    dataset["flows"].append({
        "flow_identifier": "waste-output", "flow_kind": "WASTE_FLOW",
        "output_of_activity_reference": "assembly",
        "counterpart_activity_reference": "treatment-process",
        "flow_object_reference": "waste", "flow_numerical_value": 0.25,
        "flow_unit_reference": "kg",
    })

    result = build(system, dataset)

    assert len(result.outputs) == 2
    assert len(result.external_treatments) == 1
    assert result.external_treatments[0].producer == ("inventory", "assembly")
    assert result.external_treatments[0].counterpart_reference == "treatment-process"


def test_foreground_linked_waste_remains_internal_output():
    system, dataset = example()
    dataset["flows"].extend([
        {
            "flow_identifier": "waste-output", "flow_kind": "WASTE_FLOW",
            "output_of_activity_reference": "material-production",
            "counterpart_activity_reference": "assembly",
            "flow_object_reference": "waste", "flow_numerical_value": 0.25,
            "flow_unit_reference": "kg",
        },
        {
            "flow_identifier": "waste-input", "flow_kind": "WASTE_FLOW",
            "input_to_activity_reference": "assembly",
            "counterpart_activity_reference": "material-production",
            "flow_object_reference": "waste", "flow_numerical_value": 0.25,
            "flow_unit_reference": "kg",
        },
    ])

    result = build(system, dataset)

    assert not result.external_treatments
    assert any(flow.key[1] == "waste-output" for flow in result.outputs)
    assert any(flow.provider_output[1] == "waste-output" for flow in result.inputs)


def test_rejects_missing_determining_output():
    system, dataset = example()
    dataset["activities"][0]["determining_flow_reference"] = "other-flow"

    with pytest.raises(ForegroundConstructionError, match="determining flow"):
        build(system, dataset)


def test_links_selected_activity_across_datasets_by_uri():
    system, dataset = example()
    supply_dataset = {
        "lci_dataset_identifier": "supply-dataset",
        "lci_dataset_version": "1",
        "activities": [dataset["activities"].pop(0)],
        "flows": [dataset["flows"].pop(0)],
    }
    system["lci_dataset_references"].append({
        "lci_dataset_reference_identifier": "supply",
        "lci_dataset_identifier": "supply-dataset",
        "lci_dataset_version": "1",
    })
    system["activity_references"][0] = {
        "lci_dataset_reference_identifier": "supply",
        "activity_identifier": "material-production",
        "activity_uri": "https://example.org/activities/material-production",
    }
    dataset["flows"][0]["counterpart_activity_reference"] = (
        "https://example.org/activities/material-production"
    )

    result = assemble_foreground(
        system, [dataset, supply_dataset],
        reference_flow_identifier="finished-output", quantity=4.0, unit="kg",
    )

    assert result.inputs[0].provider_output == ("supply", "material-output")


def test_rejects_nonpositive_functional_unit():
    system, dataset = example()

    with pytest.raises(ForegroundConstructionError, match="Functional-unit quantity"):
        assemble_foreground(
            system, [dataset], reference_flow_identifier="finished-output", quantity=0, unit="kg"
        )


def test_materialization_requires_resolved_boundaries():
    system, dataset = example()
    assembly = build(system, dataset)

    class UnregisteredDatabase:
        registered = False

    from see_impacts_calculation_service.foreground import materialize_foreground

    with pytest.raises(ForegroundConstructionError, match="External and elementary"):
        materialize_foreground(assembly, UnregisteredDatabase())


def test_materializes_foreground_only_graph_in_isolated_brightway_project(tmp_path):
    fixture = Path(__file__).parent / "fixtures" / "foreground_smoke.py"
    system, dataset = example()
    dataset = copy.deepcopy(dataset)
    dataset["flows"] = [
        item for item in dataset["flows"]
        if item["flow_identifier"] not in {"electricity-input", "co2-output"}
    ]
    payload = json.dumps({"product_system": system, "lci_datasets": [dataset]})
    workspace = tmp_path / "brightway"
    workspace.mkdir()
    env = {**os.environ, "BRIGHTWAY2_DIR": str(workspace)}
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    result = subprocess.run(
        [sys.executable, str(fixture), payload],
        env=env, check=True, capture_output=True, text=True,
    )
    report = json.loads(result.stdout.rsplit("\n", 2)[-2])
    assert report == {
        "activity_count": 2,
        "product_count": 2,
        "production_edges": 2,
        "input_edges": 1,
        "input_target": "material",
        "input_amount": 1.0,
    }
