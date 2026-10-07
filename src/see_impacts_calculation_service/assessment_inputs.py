"""Resolve the reference-flow demand from CE-RISE assessment inputs."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite
from typing import Any


class AssessmentInputError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(message)


@dataclass(frozen=True)
class ReferenceFlowDemand:
    product_system_identifier: str
    dataset_identifier: str
    activity_identifier: str
    flow_identifier: str
    functional_unit_quantity: float
    unit: str
    demand_scale: float


def _required_string(record: dict[str, Any], field: str, path: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise AssessmentInputError(f"{path}.{field}", "A non-empty string is required.")
    return value


def _required_object(record: dict[str, Any], field: str, path: str) -> dict[str, Any]:
    value = record.get(field)
    if not isinstance(value, dict):
        raise AssessmentInputError(f"{path}.{field}", "An object is required.")
    return value


def _required_list(record: dict[str, Any], field: str, path: str) -> list[dict[str, Any]]:
    value = record.get(field)
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, dict) for item in value)
    ):
        raise AssessmentInputError(f"{path}.{field}", "A non-empty list of objects is required.")
    return value


def _positive_number(record: dict[str, Any], field: str, path: str) -> float:
    value = record.get(field)
    try:
        number = float(value) if not isinstance(value, (bool, str)) else float("nan")
    except (TypeError, ValueError, OverflowError):
        number = float("nan")
    if not isfinite(number) or number <= 0:
        raise AssessmentInputError(f"{path}.{field}", "A positive finite number is required.")
    return number


def resolve_reference_flow(
    product_system: dict[str, Any],
    lci_datasets: list[dict[str, Any]],
    *,
    reference_flow_identifier: str,
    quantity: float,
    unit: str,
) -> ReferenceFlowDemand:
    """Resolve one selected reference activity and scale it to the requested unit."""

    system_id = _required_string(product_system, "product_system_identifier", "product_system")
    references = _required_list(product_system, "lci_dataset_references", "product_system")
    selected_activities = _required_list(product_system, "activity_references", "product_system")
    reference_flow = _required_object(product_system, "reference_flow_specification", "product_system")
    reference_path = "product_system.reference_flow_specification"
    dataset_reference_id = _required_string(
        reference_flow, "reference_flow_lci_dataset_reference_identifier", reference_path
    )
    declared_flow_id = _required_string(reference_flow, "reference_flow_identifier", reference_path)
    declared_quantity = _positive_number(reference_flow, "reference_flow_numerical_value", reference_path)
    declared_unit = _required_string(reference_flow, "reference_flow_unit_reference", reference_path)

    if reference_flow_identifier != declared_flow_id:
        raise AssessmentInputError(
            "functional_unit.reference_flow_identifier",
            "The functional unit must name the Product System reference flow.",
        )
    if unit != declared_unit:
        raise AssessmentInputError(
            "functional_unit.unit",
            "The functional unit must use the Product System reference-flow unit.",
        )

    resolved_datasets: dict[str, dict[str, Any]] = {}
    dataset_ids: dict[str, str] = {}
    for index, dataset_reference in enumerate(references):
        path = f"product_system.lci_dataset_references[{index}]"
        reference_id = _required_string(
            dataset_reference, "lci_dataset_reference_identifier", path
        )
        if reference_id in resolved_datasets:
            raise AssessmentInputError(path, f"Duplicate LCI Dataset reference {reference_id!r}.")
        candidate_id = _required_string(dataset_reference, "lci_dataset_identifier", path)
        matches = [
            item for item in lci_datasets if item.get("lci_dataset_identifier") == candidate_id
        ]
        if len(matches) != 1:
            raise AssessmentInputError(
                "lci_datasets",
                f"Expected exactly one LCI Dataset with identifier {candidate_id!r}.",
            )
        candidate = matches[0]
        expected_version = dataset_reference.get("lci_dataset_version")
        if expected_version and candidate.get("lci_dataset_version") != expected_version:
            raise AssessmentInputError(
                "lci_datasets",
                f"LCI Dataset {candidate_id!r} does not match referenced version {expected_version!r}.",
            )
        resolved_datasets[reference_id] = candidate
        dataset_ids[reference_id] = candidate_id

    selected_pairs: set[tuple[str, str]] = set()
    for index, selected in enumerate(selected_activities):
        path = f"product_system.activity_references[{index}]"
        selected_dataset_reference = _required_string(
            selected, "lci_dataset_reference_identifier", path
        )
        if selected_dataset_reference not in resolved_datasets:
            raise AssessmentInputError(
                f"{path}.lci_dataset_reference_identifier",
                "Selected activity refers to an undeclared LCI Dataset.",
            )
        selected_activity_id = _required_string(selected, "activity_identifier", path)
        pair = (selected_dataset_reference, selected_activity_id)
        if pair in selected_pairs:
            raise AssessmentInputError(path, "The same LCI activity is selected more than once.")
        selected_pairs.add(pair)
        activities = _required_list(
            resolved_datasets[selected_dataset_reference], "activities", "lci_datasets"
        )
        if sum(item.get("activity_identifier") == selected_activity_id for item in activities) != 1:
            raise AssessmentInputError(
                f"{path}.activity_identifier",
                "Selected activity must resolve to exactly one activity in its LCI Dataset.",
            )

    if dataset_reference_id not in resolved_datasets:
        raise AssessmentInputError(
            f"{reference_path}.reference_flow_lci_dataset_reference_identifier",
            "The reference flow must resolve to a declared LCI Dataset reference.",
        )
    dataset_id = dataset_ids[dataset_reference_id]
    dataset = resolved_datasets[dataset_reference_id]

    flows = _required_list(dataset, "flows", "lci_datasets")
    flow_matches = [item for item in flows if item.get("flow_identifier") == declared_flow_id]
    if len(flow_matches) != 1:
        raise AssessmentInputError(
            f"{reference_path}.reference_flow_identifier",
            "The reference flow must resolve to exactly one flow in its LCI Dataset.",
        )
    flow = flow_matches[0]
    if flow.get("flow_kind") != "PRODUCT_FLOW":
        raise AssessmentInputError(
            "lci_datasets.flows.flow_kind", "The reference flow must be a product flow."
        )
    activity_id = _required_string(flow, "output_of_activity_reference", "lci_datasets.flows")
    if flow.get("flow_unit_reference") != declared_unit:
        raise AssessmentInputError("lci_datasets.flows.flow_unit_reference", "Reference-flow units differ.")
    flow_quantity = _positive_number(flow, "flow_numerical_value", "lci_datasets.flows")
    if not isclose(flow_quantity, declared_quantity, rel_tol=1e-9):
        raise AssessmentInputError(
            f"{reference_path}.reference_flow_numerical_value",
            "The Product System reference-flow quantity differs from the LCI flow quantity.",
        )

    if (dataset_reference_id, activity_id) not in selected_pairs:
        raise AssessmentInputError(
            "product_system.activity_references",
            "The reference-flow producer must be selected by the Product System.",
        )

    demand_scale = quantity / declared_quantity
    if not isfinite(demand_scale):
        raise AssessmentInputError(
            "functional_unit.quantity", "The requested quantity cannot be scaled safely."
        )

    return ReferenceFlowDemand(
        product_system_identifier=system_id,
        dataset_identifier=dataset_id,
        activity_identifier=activity_id,
        flow_identifier=declared_flow_id,
        functional_unit_quantity=quantity,
        unit=unit,
        demand_scale=demand_scale,
    )
