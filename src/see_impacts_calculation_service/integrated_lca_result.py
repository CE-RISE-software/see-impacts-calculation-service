"""Build the CE-RISE Integrated LCA result for one calculated indicator."""

from __future__ import annotations

from typing import Any

from .foreground_calculation import ForegroundImpact


def build_integrated_lca_result(
    impact: ForegroundImpact,
    *,
    product_system_version: str,
    lci_dataset_version: str,
    product_system: dict[str, Any],
    lci_datasets: list[dict[str, Any]],
    background_project_name: str,
    background_database_name: str,
    software_version: str,
) -> dict[str, Any]:
    """Report only the assessment facts available from this calculation."""

    input_references = [
        {
            "input_role": "PRODUCT_SYSTEM",
            "source_model_identifier": "product-system",
            "source_model_version": product_system_version,
            "source_record_identifier": impact.product_system_identifier,
        }
    ]
    datasets_by_id = {dataset["lci_dataset_identifier"]: dataset for dataset in lci_datasets}
    selected_ids = dict.fromkeys(
        reference["lci_dataset_identifier"]
        for reference in product_system["lci_dataset_references"]
    )
    selected_datasets = [datasets_by_id[identifier] for identifier in selected_ids]
    input_references.extend(
        {
            "input_role": "FOREGROUND_INVENTORY",
            "source_model_identifier": "lci-dataset",
            "source_model_version": lci_dataset_version,
            "source_record_identifier": dataset["lci_dataset_identifier"],
            "source_record_version": dataset.get("lci_dataset_version"),
        }
        for dataset in selected_datasets
    )
    background_reference = {
        "input_role": "BACKGROUND_INVENTORY",
        "source_model_identifier": "brightway-project",
        "source_record_identifier": background_project_name,
    }
    if impact.background_source_artifact_uri:
        background_reference["source_artifact_uri"] = impact.background_source_artifact_uri
    input_references.append(background_reference)
    method_name = " / ".join(impact.method)
    database_info = {"background_database": background_database_name}
    if impact.background_database_version:
        database_info["database_version"] = impact.background_database_version
    software_info = {
        "software_name": "see-impacts-calculation-service",
        "software_version": software_version,
    }
    if impact.calculation_timestamp:
        software_info["calculation_timestamp"] = impact.calculation_timestamp
    indicator = {
        "assessment_dimension": "ENVIRONMENTAL",
        "indicator_identifier": method_name,
        "indicator_name": impact.method[-1],
        "assessment_method": method_name,
        "indicator_result": {
            "numeric_value": impact.score,
            "unit": impact.score_unit,
        },
    }
    if impact.method_version:
        indicator["method_version"] = impact.method_version
    if impact.factor_set_reference:
        indicator["calculation_model_or_factor_set_reference"] = impact.factor_set_reference
    return {
        "lca_analysis_instances": [
            {
                "study_metadata": {
                    "assessment_dimensions": ["ENVIRONMENTAL"],
                    "database_info": database_info,
                    "software_info": software_info,
                    "assessment_toolchain": {
                        "tool_executions": [
                            {
                                "execution_order": 1,
                                "tool_identifier": "bw2data",
                                "tool_name": "Brightway bw2data",
                                "tool_roles": ["DATA_EXTRACTION"],
                                "tool_version": impact.bw2data_version,
                            },
                            {
                                "execution_order": 2,
                                "tool_identifier": "bw2calc",
                                "tool_name": "Brightway bw2calc",
                                "tool_roles": ["INVENTORY_CALCULATION", "IMPACT_ASSESSMENT"],
                                "tool_version": impact.bw2calc_version,
                            },
                        ]
                    },
                    "functional_unit_specification": {
                        "reference_flow_identifier": impact.reference_flow_identifier,
                        "functional_unit_quantity": impact.functional_unit_quantity,
                        "functional_unit_unit": impact.functional_unit_unit,
                    },
                },
                "assessment_inputs": {"input_references": input_references},
                "assessment_results": {
                    "assessment_indicators": [indicator]
                },
            }
        ]
    }
