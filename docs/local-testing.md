# Local Testing

The current local workflow verifies that the service can safely open an approved Brightway 2
background project. It also exercises the HTTP scaffold. It does not yet demonstrate an
end-to-end impact calculation because the CE-RISE-to-Brightway mapping and acceptance fixture
are not available.

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

Run the probe before service development against a new background dataset release:

```bash
.venv/bin/see-impacts-compatibility
```

The probe activates the project and prints its registered databases and impact methods as
JSON. It does not create foreground data or run an LCIA calculation.

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

## HTTP Scaffold

Start the service from the activated virtual environment:

```bash
. .venv/bin/activate
./scripts/run-local.sh
```

In a second terminal, check the live service and background project:

```bash
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/capabilities
curl -sS http://127.0.0.1:8080/openapi.json
```

`POST /compute` validates the top-level request shape, then currently returns
`501 CALCULATION_NOT_IMPLEMENTED`. This is expected until the first acceptance fixture is
implemented.

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
