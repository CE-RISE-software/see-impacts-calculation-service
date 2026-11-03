# Deployment

## Requirements

The service runs from source with Python 3.11 or 3.12, or in a container built from the
repository's `Dockerfile`. Calculations require a reachable HEX Core service with the requested
Product System, LCI Dataset, and Integrated LCA schema versions.

The examples use HEX Core on `http://127.0.0.1:8080` and the calculator on
`http://127.0.0.1:8081`. Set `HEX_CORE_BASE_URL` to the address of HEX Core in your deployment.

## Run from Source

From the repository root, install the service and prepare its background:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install .
.venv/bin/python -m see_impacts_calculation_service.prepare_background \
  data/background/cerise_bonsai.tar.gz data/background/projects \
  --project-name cerise_bonsai
.venv/bin/see-impacts-compatibility
```

The preparation command verifies the archive and extracts the BONSAI-EF3.1 project. The
compatibility command checks that Brightway can read its databases and impact factors.

Start the calculator:

```bash
HEX_CORE_BASE_URL=http://127.0.0.1:8080 \
  .venv/bin/python -m uvicorn see_impacts_calculation_service.app:app \
    --host 127.0.0.1 --port 8081
```

## Build the Container

```bash
podman build -t see-impacts-calculation-service:local .
```

The image includes the BONSAI-EF3.1 project and runs as an unprivileged application user.
During the build, it extracts the background and checks that Brightway can read its databases
and methods. A verification failure stops the build. The default container command listens on
`0.0.0.0:8080`.

## Run the Container

On Linux, this example uses host networking to reach HEX Core on the host and runs the
calculator on port `8081`:

```bash
podman run --rm --network host \
  -e HEX_CORE_BASE_URL=http://127.0.0.1:8080 \
  see-impacts-calculation-service:local \
  python -m uvicorn see_impacts_calculation_service.app:app --host 127.0.0.1 --port 8081
```

For container-network deployments, configure `HEX_CORE_BASE_URL` with an address reachable
from the calculator container. With separate network namespaces, `127.0.0.1` refers to the
calculator container itself.

## Runtime Configuration

The service accepts the following environment variables:

- `HEX_CORE_BASE_URL`: HEX Core base URL; default `http://127.0.0.1:8080`;
- `HEX_CORE_BEARER_TOKEN`: optional service-to-service token for HEX Core validation requests;
- `HTTP_TIMEOUT_SECS`: timeout for HEX Core requests in seconds; default `30`;
- `BACKGROUND_PROJECT_DIR`: Brightway project directory; default
  `data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9`;
- `BACKGROUND_PROJECT_NAME`: expected project name from `.project-name.json`; default
  `cerise_bonsai`;
- `BACKGROUND_DATABASE_NAME`: Brightway database used for external technosphere links;
  default `BONSAI`;
- `BIOSPHERE_DATABASE_NAME`: Brightway database used for elementary flows; default `ef31_biosphere`;
- `BRIGHTWAY_WORKSPACE_DIR`: writable Brightway registry workspace; default
  `runtime/brightway` locally and `/var/lib/see-impacts/brightway` in the container image.
- `CALCULATION_TIMEOUT_SECS`: maximum time for one isolated calculation; default `900`.
- `MAX_CONCURRENT_CALCULATIONS`: maximum active Brightway calculations per server process;
  default `2`. Additional compute requests return `503` while all slots are occupied.

`POST /compute` and `POST /compute/diagnostics` call HEX Core to retrieve each requested
input model's JSON Schema and validate the Product System and LCI Dataset objects.
`POST /compute` also validates the generated Integrated LCA object through HEX Core. Provision
a reachable HEX Core registry and an appropriate service identity before using that endpoint.
The bearer token is never returned by `GET /health`.

Set the HTTP listening address and port with Uvicorn's `--host` and `--port` options.

## Background Data

The image contains the general BONSAI-EF3.1 Brightway project and treats it as
immutable. Each compute request creates a temporary project copy under
`BRIGHTWAY_WORKSPACE_DIR/requests`, calculates in a separate process, and removes the copy after
completion or timeout. The workspace must be writable and must not be inside the background
source directory. The fixed base has 49,978 BONSAI activities, the EF3.1 elementary-flow
database, and 25 registered EF3.1 method entries. Each request supplies its own CE-RISE
foreground; the background is independent of product type. The source archive and matrix
checksums are recorded in the
[background manifest](https://codeberg.org/CE-RISE-software/see-impacts-calculation-service/src/branch/main/data/background/project.json).

The BONSAI background is licensed CC BY-SA 4.0. The computing module's source code has a separate
EUPL-1.2 license. Retain the BONSAI attribution when redistributing the image.

Concurrent compute requests have separate Brightway processes and request workspaces.
Workers default to one BLAS thread to avoid multiplying numerical-library threads across
concurrent calculations; explicit numerical-library thread settings in the environment are retained.

## Service Checks

After startup, check the HTTP process, background availability, and registered methods:

```bash
curl -sS http://127.0.0.1:8081/health
curl -sS http://127.0.0.1:8081/capabilities
curl -sS http://127.0.0.1:8081/methods
```

Use `GET /health` for a lightweight liveness check. Use `GET /capabilities` as the readiness
check to confirm that Brightway can open the configured background project. The
[PV Example](pv-example.md) provides a complete calculation request and its results.
