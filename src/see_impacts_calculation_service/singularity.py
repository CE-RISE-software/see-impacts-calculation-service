"""Request-specific diagnostics for a singular Brightway technosphere."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.sparse.csgraph import connected_components


@dataclass(frozen=True)
class InvolvedActivity:
    database: str
    code: str
    name: str


@dataclass(frozen=True)
class SingularComponent:
    activities: tuple[InvolvedActivity, ...]
    reachable_from_request: bool


@dataclass(frozen=True)
class SingularityDiagnostic:
    code: str
    message: str
    components: tuple[SingularComponent, ...]
    scope: str


def _reachable_products(matrix: Any, demand: Any) -> set[int]:
    """Trace product -> producing process -> consumed products, including cycles."""

    rows = matrix.tocsr()
    columns = matrix.tocsc()
    visited_products = set(int(index) for index in np.flatnonzero(demand))
    visited_processes: set[int] = set()
    queue = deque(visited_products)
    while queue:
        product = queue.popleft()
        start, end = rows.indptr[product : product + 2]
        for position in range(start, end):
            if rows.data[position] <= 0:
                continue
            process = int(rows.indices[position])
            if process in visited_processes:
                continue
            visited_processes.add(process)
            first, last = columns.indptr[process : process + 2]
            for exchange in range(first, last):
                if columns.data[exchange] >= 0:
                    continue
                dependency = int(columns.indices[exchange])
                if dependency not in visited_products:
                    visited_products.add(dependency)
                    queue.append(dependency)
    return visited_products


def diagnose_singularity(lca: Any, bw2data: Any, *, max_component_size: int = 8) -> SingularityDiagnostic:
    """Identify small exact dependencies without guessing which input is at fault."""

    matrix = lca.technosphere_matrix
    if matrix.shape[0] != matrix.shape[1]:
        return SingularityDiagnostic(
            code="TECHNOSPHERE_NOT_SQUARE",
            message="The assembled technosphere has different product and activity counts.",
            components=(),
            scope="No singular components can be identified from a non-square matrix.",
        )
    reachable = _reachable_products(matrix, lca.demand_array)
    _, labels = connected_components(matrix, directed=True, connection="strong")
    sizes = np.bincount(labels)
    components = []
    for component_index, size in enumerate(sizes):
        if size < 2 or size > max_component_size:
            continue
        indices = np.flatnonzero(labels == component_index)
        if any(
            lca.dicts.product.reversed[int(index)] != lca.dicts.activity.reversed[int(index)]
            for index in indices
        ):
            continue
        block = matrix[indices, :][:, indices].toarray()
        if np.linalg.matrix_rank(block) == size:
            continue
        activities = []
        for index in indices:
            node = bw2data.get_node(id=lca.dicts.activity.reversed[int(index)])
            activities.append(
                InvolvedActivity(
                    database=node.key[0],
                    code=node.key[1],
                    name=node.get("name") or node.key[1],
                )
            )
        components.append(
            SingularComponent(
                activities=tuple(activities),
                reachable_from_request=any(int(index) in reachable for index in indices),
            )
        )
    components.sort(
        key=lambda item: (
            not item.reachable_from_request,
            tuple((activity.database, activity.code) for activity in item.activities),
        )
    )
    return SingularityDiagnostic(
        code="SINGULAR_TECHNOSPHERE",
        message="The assembled activity equations do not determine a unique solution; no impact score is available.",
        components=tuple(components),
        scope=(
            f"Reports demonstrably singular, aligned activity blocks of 2 to {max_component_size} nodes. "
            "Reachability traces candidate production and consumption links from the requested demand; "
            "it does not establish that foreground detail is missing or that the list is exhaustive."
        ),
    )
