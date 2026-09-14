# Architecture

## Available Components

The service is a containerized Python HTTP application with these active components:

- `app.py` exposes health, capability, OpenAPI, and API-documentation endpoints;
- `compatibility.py` opens the supplied Brightway project and reports its databases and methods;
- `config.py` reads HTTP, background-project, and Brightway-workspace settings;
- `hex_core.py` provides a source-level client for the HEX Core validation endpoint.

The HTTP application does not expose Brightway database management. Background data remains an
external deployment input.

## Background Data and Brightway State

The current local project is `cerise_bonsai`, located by default at
`data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9`. It is excluded from
Git and is not included in the container image. Deployments must mount or otherwise provision an
approved background dataset.

Brightway project state is mutable and process-global. The compatibility probe uses
`BRIGHTWAY_WORKSPACE_DIR` for this writable state and keeps the mounted background project
immutable. Do not use the background source directory as the Brightway workspace.

## API Boundary

`GET /capabilities` is the operational endpoint for checking the mounted background project.
`POST /compute` exposes a JSON schema with model-version fields for `product-system`,
`lci-dataset`, and `integrated-lca`, but returns `501 CALCULATION_NOT_IMPLEMENTED`. The Product
System object and LCI Dataset object(s) are inputs; the Integrated LCA model is the result
contract. It does not open a foreground project, call HEX Core, or produce an assessment result.

The semantic content of the input objects is the basis for building the internal Brightway
calculation. Brightway state is internal to the service; no additional mapping model, API
resource, or persisted record is part of the service boundary.
