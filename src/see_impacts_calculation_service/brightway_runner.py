"""Run a single environmental LCIA against a Brightway 2.5 project."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path

from .compatibility import BrightwayCompatibilityError, _load_brightway_project


class BrightwayCalculationError(RuntimeError):
    """The requested LCIA could not produce a finite result."""


@dataclass(frozen=True)
class ImpactScore:
    method: tuple[str, ...]
    score: float
    unit: str
    project_name: str
    database_name: str
    activity_code: str


def calculate_background_activity(
    *,
    project_dir: Path,
    workspace_dir: Path,
    project_name: str,
    database_name: str,
    activity_code: str,
    demand_amount: float,
    method: tuple[str, ...],
) -> ImpactScore:
    """Calculate one known background activity without modifying its source project."""

    if not isfinite(demand_amount) or demand_amount <= 0:
        raise BrightwayCalculationError("Demand must be a positive finite number.")
    try:
        bw2data, bw2calc = _load_brightway_project(
            project_dir.resolve(), project_name, workspace_dir.resolve()
        )
    except BrightwayCompatibilityError as error:
        raise BrightwayCalculationError(str(error)) from error

    if method not in bw2data.methods:
        raise BrightwayCalculationError(f"Impact method {method!r} is not available.")
    if database_name not in bw2data.databases:
        raise BrightwayCalculationError(f"Background database {database_name!r} is not available.")
    try:
        activity = bw2data.Database(database_name).get(activity_code)
    except Exception as error:
        raise BrightwayCalculationError(
            f"Activity {activity_code!r} is not available in {database_name!r}."
        ) from error
    if activity is None:
        raise BrightwayCalculationError(
            f"Activity {activity_code!r} is not available in {database_name!r}."
        )

    try:
        demand, data_objs, _ = bw2data.prepare_lca_inputs(
            {activity: demand_amount}, method=method
        )
        lca = bw2calc.LCA(demand=demand, data_objs=data_objs)
        lca.lci()
        lca.lcia()
        score = float(lca.score)
    except Exception as error:
        raise BrightwayCalculationError("Brightway could not complete the LCIA.") from error
    if not isfinite(score):
        raise BrightwayCalculationError("Brightway produced a non-finite LCIA score.")

    unit = bw2data.methods[method].get("unit")
    if not isinstance(unit, str) or not unit:
        raise BrightwayCalculationError(f"Impact method {method!r} has no result unit.")
    return ImpactScore(
        method=method,
        score=score,
        unit=unit,
        project_name=project_name,
        database_name=database_name,
        activity_code=activity_code,
    )
