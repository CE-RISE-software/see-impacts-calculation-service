"""Assemble CE-RISE foreground records without accessing background data."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

from .assessment_inputs import ReferenceFlowDemand, resolve_reference_flow


class ForegroundConstructionError(ValueError):
    """The supplied records cannot be assembled without guessing a link."""


ActivityKey = tuple[str, str]
FlowKey = tuple[str, str]


@dataclass(frozen=True)
class ForegroundActivity:
    key: ActivityKey
    name: str
    location: str | None


@dataclass(frozen=True)
class ForegroundOutput:
    key: FlowKey
    producer: ActivityKey
    object_reference: str | None
    amount: float
    unit: str


@dataclass(frozen=True)
class ForegroundInput:
    key: FlowKey
    consumer: ActivityKey
    provider_output: FlowKey
    amount: float
    unit: str


@dataclass(frozen=True)
class ExternalInput:
    key: FlowKey
    consumer: ActivityKey
    counterpart_reference: str | None
    object_reference: str | None
    amount: float
    unit: str


@dataclass(frozen=True)
class ExternalTreatment:
    key: FlowKey
    producer: ActivityKey
    counterpart_reference: str
    amount: float
    unit: str


@dataclass(frozen=True)
class ElementaryFlow:
    key: FlowKey
    activity: ActivityKey
    object_reference: str | None
    direction: str
    amount: float
    unit: str


@dataclass(frozen=True)
class ForegroundAssembly:
    activities: tuple[ForegroundActivity, ...]
    outputs: tuple[ForegroundOutput, ...]
    inputs: tuple[ForegroundInput, ...]
    external_inputs: tuple[ExternalInput, ...]
    external_treatments: tuple[ExternalTreatment, ...]
    elementary_flows: tuple[ElementaryFlow, ...]
    reference_output: FlowKey
    demand: ReferenceFlowDemand


def _amount(flow: dict[str, Any], key: FlowKey) -> float:
    value = flow.get("flow_numerical_value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ForegroundConstructionError(f"Flow {key!r} has no numeric amount.")
    amount = float(value)
    if not isfinite(amount) or amount <= 0:
        raise ForegroundConstructionError(f"Flow {key!r} must have a positive finite amount.")
    return amount


def _unit(flow: dict[str, Any], key: FlowKey) -> str:
    unit = flow.get("flow_unit_reference")
    if not isinstance(unit, str) or not unit.strip():
        raise ForegroundConstructionError(f"Flow {key!r} has no unit reference.")
    return unit


def assemble_foreground(
    product_system: dict[str, Any],
    lci_datasets: list[dict[str, Any]],
    *,
    reference_flow_identifier: str,
    quantity: float,
    unit: str,
) -> ForegroundAssembly:
    """Build selected activities and exchanges; leave external demands unresolved."""

    if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or not isfinite(quantity) or quantity <= 0:
        raise ForegroundConstructionError("Functional-unit quantity must be positive and finite.")
    demand = resolve_reference_flow(
        product_system,
        lci_datasets,
        reference_flow_identifier=reference_flow_identifier,
        quantity=quantity,
        unit=unit,
    )
    datasets_by_id = {item["lci_dataset_identifier"]: item for item in lci_datasets}
    reference_to_dataset = {
        item["lci_dataset_reference_identifier"]: datasets_by_id[item["lci_dataset_identifier"]]
        for item in product_system["lci_dataset_references"]
    }
    selected: dict[ActivityKey, dict[str, Any]] = {}
    selected_aliases: dict[ActivityKey, set[str]] = {}
    for reference in product_system["activity_references"]:
        dataset_ref = reference["lci_dataset_reference_identifier"]
        activity_id = reference["activity_identifier"]
        dataset = reference_to_dataset[dataset_ref]
        selected[(dataset_ref, activity_id)] = next(
            item for item in dataset["activities"] if item.get("activity_identifier") == activity_id
        )
        selected_aliases[(dataset_ref, activity_id)] = {
            alias for alias in (activity_id, reference.get("activity_uri")) if isinstance(alias, str)
        }

    activities = tuple(
        ForegroundActivity(
            key=key,
            name=record.get("activity_name") or key[1],
            location=record.get("location_reference"),
        )
        for key, record in selected.items()
    )
    outputs: list[ForegroundOutput] = []
    external_treatments: list[ExternalTreatment] = []
    pending_inputs: list[tuple[FlowKey, ActivityKey, dict[str, Any]]] = []
    elementary: list[ElementaryFlow] = []
    seen_flows: set[FlowKey] = set()

    for dataset_ref, dataset in reference_to_dataset.items():
        for flow in dataset.get("flows", []):
            flow_id = flow.get("flow_identifier")
            if not isinstance(flow_id, str) or not flow_id:
                raise ForegroundConstructionError(f"Dataset {dataset_ref!r} contains a flow without an identifier.")
            key = (dataset_ref, flow_id)
            if key in seen_flows:
                raise ForegroundConstructionError(f"Duplicate flow identifier {key!r}.")
            seen_flows.add(key)
            producer = (dataset_ref, flow.get("output_of_activity_reference"))
            consumer = (dataset_ref, flow.get("input_to_activity_reference"))
            producer_selected = producer in selected
            consumer_selected = consumer in selected
            if not producer_selected and not consumer_selected:
                continue
            kind = flow.get("flow_kind")
            direction = flow.get("flow_direction")
            if kind in ("PRODUCT_FLOW", "WASTE_FLOW"):
                if producer_selected:
                    if direction not in (None, "OUTPUT"):
                        raise ForegroundConstructionError(f"Output flow {key!r} has conflicting direction.")
                    counterpart = flow.get("counterpart_activity_reference")
                    foreground_counterpart = any(
                        counterpart in aliases for aliases in selected_aliases.values()
                    )
                    if (
                        kind == "WASTE_FLOW"
                        and isinstance(counterpart, str)
                        and counterpart
                        and not foreground_counterpart
                    ):
                        external_treatments.append(
                            ExternalTreatment(
                                key, producer, counterpart, _amount(flow, key), _unit(flow, key)
                            )
                        )
                    else:
                        outputs.append(
                            ForegroundOutput(
                                key=key,
                                producer=producer,
                                object_reference=flow.get("flow_object_reference"),
                                amount=_amount(flow, key),
                                unit=_unit(flow, key),
                            )
                        )
                if consumer_selected:
                    if direction not in (None, "INPUT"):
                        raise ForegroundConstructionError(f"Input flow {key!r} has conflicting direction.")
                    pending_inputs.append((key, consumer, flow))
            elif kind == "ELEMENTARY_FLOW":
                if producer_selected == consumer_selected:
                    raise ForegroundConstructionError(
                        f"Elementary flow {key!r} must attach to one selected activity."
                    )
                resolved_direction = direction or ("OUTPUT" if producer_selected else "INPUT")
                if resolved_direction != ("OUTPUT" if producer_selected else "INPUT"):
                    raise ForegroundConstructionError(f"Elementary flow {key!r} has conflicting direction.")
                elementary.append(
                    ElementaryFlow(
                        key=key,
                        activity=producer if producer_selected else consumer,
                        object_reference=flow.get("flow_object_reference"),
                        direction=resolved_direction,
                        amount=_amount(flow, key),
                        unit=_unit(flow, key),
                    )
                )
            else:
                raise ForegroundConstructionError(f"Flow {key!r} has unsupported kind {kind!r}.")

    outputs_by_producer: dict[ActivityKey, list[ForegroundOutput]] = {}
    for output in outputs:
        outputs_by_producer.setdefault(output.producer, []).append(output)
    internal_inputs: list[ForegroundInput] = []
    external_inputs: list[ExternalInput] = []
    for key, consumer, flow in pending_inputs:
        counterpart = flow.get("counterpart_activity_reference") or flow.get(
            "output_of_activity_reference"
        )
        object_ref = flow.get("flow_object_reference")
        amount = _amount(flow, key)
        input_unit = _unit(flow, key)
        candidate_producers = (
            [activity for activity in selected if counterpart in selected_aliases[activity]]
            if counterpart else list(selected) if object_ref else []
        )
        candidates = [
            output
            for producer in candidate_producers
            for output in outputs_by_producer.get(producer, [])
            if (object_ref is None or output.object_reference == object_ref)
            and output.unit == input_unit
        ]
        if len(candidates) > 1:
            raise ForegroundConstructionError(f"Input flow {key!r} matches multiple foreground outputs.")
        if len(candidates) == 1:
            internal_inputs.append(
                ForegroundInput(key, consumer, candidates[0].key, amount, input_unit)
            )
        else:
            if candidate_producers and counterpart:
                raise ForegroundConstructionError(
                    f"Input flow {key!r} does not match the selected producer's output and unit."
                )
            external_inputs.append(
                ExternalInput(key, consumer, counterpart, object_ref, amount, input_unit)
            )

    reference_dataset_ref = product_system["reference_flow_specification"]["reference_flow_lci_dataset_reference_identifier"]
    reference_candidates = [
        output for output in outputs
        if output.key == (reference_dataset_ref, demand.flow_identifier)
        and output.producer[1] == demand.activity_identifier
    ]
    if len(reference_candidates) != 1:
        raise ForegroundConstructionError("The reference flow is not a unique selected output.")
    for activity in activities:
        produced = outputs_by_producer.get(activity.key, [])
        if not produced:
            raise ForegroundConstructionError(f"Selected activity {activity.key!r} has no output flow.")
        determining_flow = selected[activity.key].get("determining_flow_reference")
        if determining_flow and not any(
            output.key[1] == determining_flow for output in produced
        ):
            raise ForegroundConstructionError(
                f"Selected activity {activity.key!r} has no matching determining flow."
            )

    return ForegroundAssembly(
        activities=activities,
        outputs=tuple(outputs),
        inputs=tuple(internal_inputs),
        external_inputs=tuple(external_inputs),
        external_treatments=tuple(external_treatments),
        elementary_flows=tuple(elementary),
        reference_output=reference_candidates[0].key,
        demand=demand,
    )
