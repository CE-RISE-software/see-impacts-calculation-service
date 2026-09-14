# Architecture

## Service Boundary

The SEE impacts calculation service is a containerized Python HTTP service for impact
assessment. Its responsibility is to translate validated CE-RISE assessment inputs into a
temporary Brightway calculation and return a validated `integrated-lca` result record.

Brightway and approved background projects remain internal implementation concerns. Callers
interact through HTTP and CE-RISE model payloads rather than Brightway databases or code.

## Model Responsibilities

- `product-system` supplies the selected activity assembly and reference-flow scaling.
- `lci-dataset` supplies the selected foreground activity and flow graph.
- `integrated-lca` structures the computed study metadata, methods, results,
  interpretation, and reporting output.

The service must not redefine these models. It delegates validation to `hex-core-service`
before mapping inputs and after constructing the integrated-lca result.

## Intended Computation Flow

1. The caller sends CE-RISE model versions, a Product System payload, materialized LCI
   Dataset payloads, and assessment context to `POST /compute`.
2. The service forwards the caller's bearer token while delegating model validation to
   `hex-core-service`.
3. A versioned mapping bundle resolves CE-RISE identifiers, units, activities, and
   exchanges to the configured Brightway project.
4. The service creates a temporary foreground database, performs the requested inventory
   and impact calculations, and removes that temporary database.
5. The service constructs and validates the Integrated LCA record, then returns it with
   model validation reports and calculation provenance.

## Background Data and Brightway State

The current local project is `cerise_bonsai`, located by default at
`data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9`. It is excluded from
Git and is not included in the container image. Deployments must mount or otherwise provision an
approved background dataset.

Brightway project state is mutable and process-global. A deployed calculation worker must
therefore have exclusive access to its writable project workspace. Background source data
should be treated as immutable; foreground databases belong in a separate writable
workspace and are removed after each completed calculation. `BRIGHTWAY_WORKSPACE_DIR` points
to that writable workspace and must not be the background source directory.

## Runtime Components

- `app.py` exposes the HTTP application and reserved computation contract.
- `compatibility.py` activates the supplied Brightway project without modifying source data
  and reports its databases and methods.
- `hex_core.py` contains the client used for delegated model validation. It is not wired into
  the scaffold's `POST /compute` implementation yet.
- `config.py` reads runtime configuration independently from CE-RISE assessment payloads.

## Current Implementation Boundary

The scaffold exposes service health, capability probing, an OpenAPI document, and the
reserved compute request shape. It does not yet map CE-RISE data to Brightway, invoke HEX
Core validation, create a foreground database, or calculate results. Those steps begin once a
versioned mapping design and an end-to-end acceptance fixture are available.
