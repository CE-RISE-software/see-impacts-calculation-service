"""Calculate CE-RISE foreground against a disposable Brightway background."""

import json
import sys
from dataclasses import asdict
from pathlib import Path

import bw2data as bd

from see_impacts_calculation_service.foreground import assemble_foreground
from see_impacts_calculation_service.foreground_calculation import (
    ForegroundCalculationError,
    calculate_foreground,
)


def sample_inputs(
    counterpart: str,
    input_unit: str = "kg",
    input_amount: float = 2.0,
    waste_amount: float | None = None,
):
    system = {
        "product_system_identifier": "test-system",
        "lci_dataset_references": [{
            "lci_dataset_reference_identifier": "inventory",
            "lci_dataset_identifier": "dataset",
            "lci_dataset_version": "1",
        }],
        "activity_references": [{
            "lci_dataset_reference_identifier": "inventory",
            "activity_identifier": "make-product",
        }],
        "reference_flow_specification": {
            "reference_flow_lci_dataset_reference_identifier": "inventory",
            "reference_flow_identifier": "product-output",
            "reference_flow_numerical_value": 1.0,
            "reference_flow_unit_reference": "kg",
        },
    }
    dataset = {
        "lci_dataset_identifier": "dataset",
        "lci_dataset_version": "1",
        "activities": [{"activity_identifier": "make-product"}],
        "flows": [
            {
                "flow_identifier": "product-output",
                "flow_kind": "PRODUCT_FLOW",
                "output_of_activity_reference": "make-product",
                "flow_object_reference": "product",
                "flow_numerical_value": 1.0,
                "flow_unit_reference": "kg",
            },
            {
                "flow_identifier": "background-input",
                "flow_kind": "PRODUCT_FLOW",
                "input_to_activity_reference": "make-product",
                "counterpart_activity_reference": counterpart,
                "flow_object_reference": "background-product",
                "flow_numerical_value": input_amount,
                "flow_unit_reference": input_unit,
            },
            {
                "flow_identifier": "direct-emission",
                "flow_kind": "ELEMENTARY_FLOW",
                "output_of_activity_reference": "make-product",
                "flow_object_reference": "co2",
                "flow_numerical_value": 0.5,
                "flow_unit_reference": "kg",
            },
        ],
    }
    if waste_amount is not None:
        dataset["flows"].append({
            "flow_identifier": "treated-waste",
            "flow_kind": "WASTE_FLOW",
            "output_of_activity_reference": "make-product",
            "counterpart_activity_reference": counterpart,
            "flow_object_reference": "waste",
            "flow_numerical_value": waste_amount,
            "flow_unit_reference": "kg",
        })
    return system, dataset


def main() -> None:
    source = Path(sys.argv[1])
    workspace = Path(sys.argv[2])
    counterpart = sys.argv[3]
    input_unit = sys.argv[4] if len(sys.argv) > 4 else "kg"
    input_amount = float(sys.argv[5]) if len(sys.argv) > 5 else 2.0
    waste_amount = float(sys.argv[6]) if len(sys.argv) > 6 else None
    system, dataset = sample_inputs(counterpart, input_unit, input_amount, waste_amount)
    assembly = assemble_foreground(
        system, [dataset],
        reference_flow_identifier="product-output", quantity=4.0, unit="kg",
    )
    try:
        result = calculate_foreground(
            assembly,
            project_dir=source,
            workspace_dir=workspace,
            project_name="synthetic",
            background_database_name="background",
            biosphere_database_name="biosphere",
            method=("synthetic", "climate"),
        )
    except ForegroundCalculationError as error:
        if error.diagnostic is None:
            raise
        print(json.dumps({"status": "not_calculable", "diagnostic": asdict(error.diagnostic)}))
        return
    print(json.dumps({"impact": asdict(result), "databases": sorted(bd.databases)}))


if __name__ == "__main__":
    main()
