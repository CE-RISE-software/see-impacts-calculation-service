"""Materialize a foreground-only CE-RISE graph in a disposable Brightway project."""

import json
import sys

import bw2data as bd

from see_impacts_calculation_service.foreground import assemble_foreground, materialize_foreground


def main() -> None:
    payload = json.loads(sys.argv[1])
    bd.projects.set_current("foreground-smoke")
    assembly = assemble_foreground(
        payload["product_system"], payload["lci_datasets"],
        reference_flow_identifier="finished-output", quantity=4.0, unit="kg",
    )
    database = bd.Database("foreground")
    materialize_foreground(assembly, database)
    nodes = list(database)
    edges = [edge for node in nodes if node.get("type") == "process" for edge in node.exchanges()]
    input_edges = [edge for edge in edges if edge.get("type") == "technosphere"]
    print(json.dumps({
        "activity_count": sum(node.get("type") == "process" for node in nodes),
        "product_count": sum(node.get("type") == "product" for node in nodes),
        "production_edges": sum(edge.get("type") == "production" for edge in edges),
        "input_edges": len(input_edges),
        "input_target": input_edges[0].input.get("name"),
        "input_amount": float(input_edges[0].get("amount")),
    }))


if __name__ == "__main__":
    main()
