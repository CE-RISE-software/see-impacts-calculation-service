# Local Testing

Run the complete test suite or prepare the bundled background for a local HTTP service.

## Setup

Create a virtual environment and install the service with its test dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-test.txt
```

## Tests

```bash
.venv/bin/python -m pytest
```

The suite builds a fresh Brightway project from the bundled seed and BONSAI IO release, then
sends the PV fixture to `POST /compute`. It fetches the latest published Product System, LCI
Dataset, and Integrated LCA schemas from Codeberg to validate the inputs and result. The same
suite checks concurrent requests with a synthetic background. No manually prepared background
project, live HEX Core, or opt-in flag is required. Codeberg runs the core tests on
`codeberg-medium` and the PV input/output record validation on `codeberg-small` for pushes,
pull requests, and releases. The full PV calculation remains in the local suite; the hosted PV
job does not run Brightway or check the calculated score.

## Local Background

Build the local background from the seed project and bundled BONSAI IO files:

```bash
mkdir -p data/background/projects
tar -xzf data/background/cerise_bonsai.tar.gz -C data/background/projects
.venv/bin/python -m see_impacts_calculation_service.import_bonsai \
  data/background/bonsai-3.8-beta2 \
  data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9 \
  --project-name cerise_bonsai
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

To use a non-default location without changing the environment permanently:

```bash
BACKGROUND_PROJECT_DIR=/path/to/project \
BRIGHTWAY_WORKSPACE_DIR=/tmp/see-impacts-brightway \
.venv/bin/see-impacts-compatibility
```

## HTTP Service

Start the service from the repository root. Replace the example HEX Core address with one
reachable from this machine before sending compute requests:

```bash
HEX_CORE_BASE_URL=http://hex-core-host:8080 \
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
and Integrated LCA schemas. It validates the inputs, calculates the requested method, and
validates the generated output. Use the [PV request](api-overview.md#send-a-request) to exercise
this path. Invalid inputs or unresolved links return `422`; a singular technosphere returns a
`not_calculable` diagnostic without a score. `GET /capabilities` checks that the background
project opens, not whether a particular request can be calculated.

## Container Smoke Test

Build the image locally:

```bash
podman build -t see-impacts-calculation-service:local .
```

Run it with the included BONSAI background project:

```bash
podman run --rm -p 8080:8080 \
  see-impacts-calculation-service:local
```

Then call `GET /capabilities`. A successful response proves that the container can inspect the
bundled background project.
