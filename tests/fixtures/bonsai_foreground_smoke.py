"""Exercise the internal foreground calculation against the supplied BONSAI data."""

import json
import sys
from dataclasses import asdict
from pathlib import Path

from see_impacts_calculation_service.foreground import assemble_foreground
from see_impacts_calculation_service.foreground_calculation import (
    ForegroundCalculationError,
    calculate_foreground,
)


def main() -> None:
    system = {
        "product_system_identifier": "background-link-smoke",
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
                "flow_identifier": "product-output", "flow_kind": "PRODUCT_FLOW",
                "output_of_activity_reference": "make-product", "flow_numerical_value": 1.0,
                "flow_unit_reference": "kg",
            },
            {
                "flow_identifier": "electricity-input", "flow_kind": "PRODUCT_FLOW",
                "input_to_activity_reference": "make-product",
                "counterpart_activity_reference": "M_electricity|DE",
                "flow_numerical_value": 1.0,
                "flow_unit_reference": "kWh",
            },
        ],
    }
    assembly = assemble_foreground(
        system, [dataset], reference_flow_identifier="product-output", quantity=1.0, unit="kg"
    )
    try:
        impact = calculate_foreground(
            assembly,
            project_dir=Path(sys.argv[1]),
            workspace_dir=Path(sys.argv[2]),
            project_name="cerise_bonsai",
            background_database_name="bonsai",
            biosphere_database_name="biosphere3",
            method=("CML v4.8 2016", "climate change", "global warming potential (GWP100)"),
        )
        print(json.dumps({"status": "calculable", "impact": asdict(impact)}))
    except ForegroundCalculationError as error:
        if error.diagnostic is None:
            raise
        print(json.dumps({"status": "not_calculable", "diagnostic": asdict(error.diagnostic)}))


if __name__ == "__main__":
    main()
