"""Calculate an assembled foreground using read-only Brightway background data."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

import pint
from bw_processing.matrix_entry import MatrixEntry, MatrixName, create_datapackage_from_entries
from scipy.sparse.linalg import MatrixRankWarning

from .compatibility import BrightwayCompatibilityError, _load_brightway_project, _version_string
from .foreground import ForegroundAssembly
from .singularity import SingularityDiagnostic, diagnose_singularity


class ForegroundCalculationError(RuntimeError):
    """A foreground link or calculation could not be completed safely."""

    def __init__(self, message: str, diagnostic: SingularityDiagnostic | None = None) -> None:
        self.diagnostic = diagnostic
        super().__init__(message)


@dataclass(frozen=True)
class ForegroundImpact:
    product_system_identifier: str
    reference_flow_identifier: str
    functional_unit_quantity: float
    functional_unit_unit: str
    method: tuple[str, ...]
    score: float
    score_unit: str
    bw2data_version: str
    bw2calc_version: str


_UNITS = pint.UnitRegistry()


def _converted_amount(amount: float, source_unit: str, target_unit: str, label: str) -> float:
    try:
        converted = (amount * _UNITS.Unit(source_unit)).to(target_unit).magnitude
    except (pint.UndefinedUnitError, pint.DimensionalityError, ValueError) as error:
        raise ForegroundCalculationError(
            f"{label} unit {source_unit!r} cannot be converted to {target_unit!r}."
        ) from error
    if not isfinite(converted) or converted <= 0:
        raise ForegroundCalculationError(f"{label} converted amount is not positive and finite.")
    return float(converted)


def _node(database: Any, code: str, label: str) -> Any:
    try:
        node = database.get(code)
    except Exception as error:
        raise ForegroundCalculationError(
            f"{label} identifier {code!r} was not found in database {database.name!r}."
        ) from error
    if node is None:
        raise ForegroundCalculationError(
            f"{label} identifier {code!r} was not found in database {database.name!r}."
        )
    return node


def _foreground_datapackage(
    assembly: ForegroundAssembly,
    *,
    next_id: int,
    background_database: Any,
    biosphere_database: Any,
) -> tuple[Any, int]:
    activity_ids = {
        activity.key: next_id + index for index, activity in enumerate(assembly.activities)
    }
    next_id += len(activity_ids)
    product_ids = {
        output.key: next_id + index for index, output in enumerate(assembly.outputs)
    }
    technosphere = [
        MatrixEntry(
            row=product_ids[output.key],
            col=activity_ids[output.producer],
            amount=output.amount,
            reference=output.key == assembly.reference_output,
        )
        for output in assembly.outputs
    ]
    technosphere.extend(
        MatrixEntry(
            row=product_ids[flow.provider_output],
            col=activity_ids[flow.consumer],
            amount=flow.amount,
            flip=True,
        )
        for flow in assembly.inputs
    )
    for flow in assembly.external_inputs:
        if not flow.counterpart_reference:
            raise ForegroundCalculationError(
                f"External flow {flow.key!r} has no counterpart activity identifier."
            )
        provider = _node(background_database, flow.counterpart_reference, "Background activity")
        if provider.get("type") not in (None, "process", "processwithreferenceproduct"):
            raise ForegroundCalculationError(
                f"Background activity {flow.counterpart_reference!r} is not a product demand node."
            )
        if provider.get("type") == "process" and not any(
            exchange.input.id == provider.id for exchange in provider.production()
        ):
            raise ForegroundCalculationError(
                f"Background process {flow.counterpart_reference!r} has no matching product node."
            )
        provider_unit = provider.get("unit")
        if not isinstance(provider_unit, str):
            raise ForegroundCalculationError(
                f"Background activity {flow.counterpart_reference!r} has no unit."
            )
        technosphere.append(
            MatrixEntry(
                row=provider.id,
                col=activity_ids[flow.consumer],
                amount=_converted_amount(flow.amount, flow.unit, provider_unit, str(flow.key)),
                flip=True,
            )
        )

    biosphere = []
    for flow in assembly.elementary_flows:
        if not flow.object_reference:
            raise ForegroundCalculationError(
                f"Elementary flow {flow.key!r} has no biosphere flow identifier."
            )
        target = _node(biosphere_database, flow.object_reference, "Biosphere flow")
        target_unit = target.get("unit")
        if not isinstance(target_unit, str):
            raise ForegroundCalculationError(
                f"Biosphere flow {flow.object_reference!r} has no unit."
            )
        biosphere.append(
            MatrixEntry(
                row=target.id,
                col=activity_ids[flow.activity],
                amount=_converted_amount(flow.amount, flow.unit, target_unit, str(flow.key)),
            )
        )

    data = {MatrixName.technosphere: technosphere}
    if biosphere:
        data[MatrixName.biosphere] = biosphere
    return create_datapackage_from_entries(data, name="ce-rise-foreground"), product_ids[assembly.reference_output]


def calculate_foreground(
    assembly: ForegroundAssembly,
    *,
    project_dir: Path,
    workspace_dir: Path,
    project_name: str,
    background_database_name: str,
    biosphere_database_name: str,
    method: tuple[str, ...],
) -> ForegroundImpact:
    """Run one LCIA without persisting foreground nodes or altering background data."""

    try:
        bd, bc = _load_brightway_project(
            project_dir.resolve(), project_name, workspace_dir.resolve()
        )
    except BrightwayCompatibilityError as error:
        raise ForegroundCalculationError(str(error)) from error
    if method not in bd.methods:
        raise ForegroundCalculationError(f"Impact method {method!r} is unavailable.")
    for name in (background_database_name, biosphere_database_name):
        if name not in bd.databases:
            raise ForegroundCalculationError(f"Brightway database {name!r} is unavailable.")

    background = bd.Database(background_database_name)
    biosphere = bd.Database(biosphere_database_name)
    highest_id = max(node.id for name in bd.databases for node in bd.Database(name))
    foreground_package, reference_id = _foreground_datapackage(
        assembly,
        next_id=highest_id + 1,
        background_database=background,
        biosphere_database=biosphere,
    )
    packages = [bd.Database(name).datapackage() for name in bd.databases]
    packages.extend((bd.Method(method).datapackage(), foreground_package))
    try:
        calculation = bc.LCA(
            demand={reference_id: assembly.demand.functional_unit_quantity},
            data_objs=packages,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("error", MatrixRankWarning)
            calculation.lci()
            calculation.lcia()
        score = float(calculation.score)
    except MatrixRankWarning as error:
        diagnostic = diagnose_singularity(calculation, bd)
        raise ForegroundCalculationError(
            "The combined technosphere is singular; no unique LCIA score is available.",
            diagnostic=diagnostic,
        ) from error
    except Exception as error:
        raise ForegroundCalculationError(
            "Brightway could not solve the combined foreground and background calculation."
        ) from error
    if not isfinite(score):
        raise ForegroundCalculationError("Brightway produced a non-finite LCIA score.")
    score_unit = bd.methods[method].get("unit")
    if not isinstance(score_unit, str) or not score_unit:
        raise ForegroundCalculationError(f"Impact method {method!r} has no result unit.")
    return ForegroundImpact(
        product_system_identifier=assembly.demand.product_system_identifier,
        reference_flow_identifier=assembly.demand.flow_identifier,
        functional_unit_quantity=assembly.demand.functional_unit_quantity,
        functional_unit_unit=assembly.demand.unit,
        method=method,
        score=score,
        score_unit=score_unit,
        bw2data_version=_version_string(getattr(bd, "__version__", "unknown")),
        bw2calc_version=_version_string(getattr(bc, "__version__", "unknown")),
    )
