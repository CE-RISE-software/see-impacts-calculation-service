# Local Testing

This page shows how to verify that the service can safely open an approved Brightway 2.5
background project, run its tests, and start the HTTP service.

## Setup

Create a virtual environment and install the service with its test dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

The default background project location is
`data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9`. Override it with
`BACKGROUND_PROJECT_DIR` when an approved dataset is located elsewhere. The separate
`BRIGHTWAY_WORKSPACE_DIR` holds Brightway's writable project registry and defaults to
`runtime/brightway`.

## Brightway Compatibility Probe

Run the probe against the configured background project:

```bash
.venv/bin/see-impacts-compatibility
```

The probe activates the supplied data and reports the registered databases and methods as
JSON. It also reads a record and its exchanges from each database, opens their processed
datapackages, and loads factors from one method. It does not create foreground data or run an
LCIA calculation. The writable workspace is separate from the read-only source archive.

Run the optional regression check against an approved local snapshot by setting its path:

```bash
SEE_IMPACTS_TEST_BACKGROUND_DIR="$PWD/data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9" \
  .venv/bin/python -m pytest tests/test_background_access.py
```

The optional access test verifies that the supplied archive opens. A separate optional test
attempts a foreground calculation against that archive and checks the singular-matrix
diagnostic observed for its selected demand:

```bash
SEE_IMPACTS_TEST_BACKGROUND_DIR="$PWD/data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9" \
  .venv/bin/python -m pytest tests/test_foreground_calculation.py::test_supplied_bonsai_foreground_run_reports_singular_matrix
```

The default suite also exercises a complete HTTP compute request against a disposable
synthetic Brightway project, using a HEX Core validation stub. This verifies the numerical
calculation and output-validation call, not a live HEX Core deployment or a successful BONSAI
score.

To use a non-default location without changing the environment permanently:

```bash
BACKGROUND_PROJECT_DIR=/path/to/project \
BRIGHTWAY_WORKSPACE_DIR=/tmp/see-impacts-brightway \
.venv/bin/see-impacts-compatibility
```

## Unit Tests

```bash
.venv/bin/python -m pytest
```

Codeberg runs the same suite on `codeberg-small` for pushes and pull requests. CI builds its
synthetic Brightway fixture locally; the optional tests requiring the separately supplied
BONSAI archive remain skipped.

## HTTP Service

Start the service from the repository root:

```bash
.venv/bin/python -m uvicorn see_impacts_calculation_service.app:app --host 127.0.0.1 --port 8080
```

In a second terminal, check the live service and background project:

```bash
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/capabilities
curl -sS http://127.0.0.1:8080/methods
curl -sS http://127.0.0.1:8080/openapi.json
```

`POST /compute` requires a reachable HEX Core with the requested Product System, LCI Dataset,
and Integrated LCA schemas. It validates both input models, calculates the requested method,
and validates the generated output. Invalid inputs or unresolved links return `422`; a singular
technosphere returns a `not_calculable` diagnostic without a score. Use `GET /capabilities` to
check that the background project opens, not to establish that a specific request is solvable.

## Container Smoke Test

Build the image locally:

```bash
podman build -t see-impacts-calculation-service:local .
```

Run it with the approved local background directory mounted read-only:

```bash
podman run --rm -p 8080:8080 \
  -e BACKGROUND_PROJECT_DIR=/data/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9 \
  -e BRIGHTWAY_WORKSPACE_DIR=/var/lib/see-impacts/brightway \
  -v "$PWD/data/background:/data:ro,Z" \
  see-impacts-calculation-service:local
```

Then call `GET /capabilities`. A successful response proves that the container can inspect the
mounted background project without baking it into the image.
