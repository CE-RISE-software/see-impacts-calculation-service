"""Create and calculate a tiny Brightway project in separate processes."""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import asdict
from pathlib import Path


def build(builder_dir: Path, source_dir: Path, *, singular: bool = False) -> None:
    builder_dir.mkdir(parents=True)
    os.environ["BRIGHTWAY2_DIR"] = str(builder_dir)
    import bw2data as bd

    bd.projects.set_current("synthetic")
    biosphere = bd.Database("biosphere")
    biosphere.register()
    co2 = biosphere.new_node(code="co2", name="Carbon dioxide", type="emission", unit="kg")
    co2.save()

    database = bd.Database("background")
    database.register()
    activity = database.new_node(
        code="activity-1", name="Synthetic activity", **{"reference product": "Synthetic product"},
        type="process", unit="kg"
    )
    activity.save()
    activity.new_edge(input=activity, amount=1.0, type="production").save()
    activity.new_edge(input=co2, amount=2.0, type="biosphere").save()

    if singular:
        for prefix in ("reachable", "separate"):
            first = database.new_node(code=f"{prefix}-a", name=f"{prefix} activity A", type="process", unit="kg")
            second = database.new_node(code=f"{prefix}-b", name=f"{prefix} activity B", type="process", unit="kg")
            first.save()
            second.save()
            first.new_edge(input=first, amount=1.0, type="production").save()
            second.new_edge(input=second, amount=1.0, type="production").save()
            first.new_edge(input=second, amount=1.0, type="technosphere").save()
            second.new_edge(input=first, amount=1.0, type="technosphere").save()
            if prefix == "reachable":
                activity.new_edge(input=first, amount=1.0, type="technosphere").save()

    method = bd.Method(("synthetic", "climate"))
    method.register(unit="kg CO2-eq")
    method.write([(co2.key, 3.0)])
    shutil.copytree(bd.projects.dir, source_dir)
    (source_dir / ".project-name.json").write_text(
        json.dumps({"name": "synthetic"}), encoding="utf-8"
    )


def calculate(source_dir: Path, workspace_dir: Path) -> None:
    from see_impacts_calculation_service.brightway_runner import calculate_background_activity

    result = calculate_background_activity(
        project_dir=source_dir,
        workspace_dir=workspace_dir,
        project_name="synthetic",
        database_name="background",
        activity_code="activity-1",
        demand_amount=2.0,
        method=("synthetic", "climate"),
    )
    print(json.dumps(asdict(result)))


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "build":
        build(Path(sys.argv[2]), Path(sys.argv[3]))
    elif command == "build-singular":
        build(Path(sys.argv[2]), Path(sys.argv[3]), singular=True)
    elif command == "calculate":
        calculate(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        raise ValueError(f"Unknown command: {command}")
