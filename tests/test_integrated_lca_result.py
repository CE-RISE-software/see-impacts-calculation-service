from see_impacts_calculation_service.foreground_calculation import ForegroundImpact
from see_impacts_calculation_service.integrated_lca_result import build_integrated_lca_result


def test_result_references_only_selected_input_datasets():
    impact = ForegroundImpact(
        product_system_identifier="system-1",
        reference_flow_identifier="flow-1",
        functional_unit_quantity=4.0,
        functional_unit_unit="kg",
        method=("example", "method"),
        score=12.5,
        score_unit="kg CO2-eq",
        bw2data_version="4.7",
        bw2calc_version="2.5.0",
    )

    result = build_integrated_lca_result(
        impact,
        product_system_version="0.2.0",
        lci_dataset_version="0.2.0",
        product_system={"lci_dataset_references": [{"lci_dataset_identifier": "used"}]},
        lci_datasets=[
            {"lci_dataset_identifier": "used", "lci_dataset_version": "1"},
            {"lci_dataset_identifier": "unused", "lci_dataset_version": "1"},
        ],
        background_project_name="synthetic",
        background_database_name="background",
        software_version="0.0.1",
    )

    references = result["lca_analysis_instances"][0]["assessment_inputs"]["input_references"]
    assert [reference["source_record_identifier"] for reference in references] == [
        "system-1",
        "used",
        "synthetic",
    ]
    metadata = result["lca_analysis_instances"][0]["study_metadata"]
    assert metadata["database_info"] == {"background_database": "background"}
    assert metadata["software_info"] == {
        "software_name": "see-impacts-calculation-service",
        "software_version": "0.0.1",
    }
    assert [
        (item["tool_identifier"], item["tool_version"])
        for item in metadata["assessment_toolchain"]["tool_executions"]
    ] == [("bw2data", "4.7"), ("bw2calc", "2.5.0")]
