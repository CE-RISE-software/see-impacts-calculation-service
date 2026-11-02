# Deployment

## Service Form

This project is deployed as a containerized HTTP service. The `Dockerfile` extracts the bundled
BONSAI-EF3.1 Brightway project and verifies that Brightway can read its databases and methods.
A failed verification stops the image build. The background and characterization factors are
already linked in the archive; no separate IO importer is installed or run.

## Image Publication

Pushing a `v*.*.*` tag to the canonical Codeberg repository triggers the Forgejo release
workflow. The core tests and PV record-validation job must pass before it builds and publishes;
the local test suite includes the full BONSAI PV calculation, which hosted CI does not run:

```text
$REGISTRY_HOST/$REGISTRY_NAMESPACE/see-impacts-calculation:<tag>
$REGISTRY_HOST/$REGISTRY_NAMESPACE/see-impacts-calculation:latest
```

The workflow needs these repository-level settings:

- variables: `REGISTRY_HOST`, `REGISTRY_NAMESPACE`;
- secrets: `REGISTRY_USERNAME`, `REGISTRY_PASSWORD`.

The existing CE-RISE registry convention resolves these to an image such as
`rg.fr-par.scw.cloud/ce-rise-software/see-impacts-calculation:<tag>`. A release tag must never
be pushed before the registry settings are configured.

## Build Locally

```bash
podman build -t see-impacts-calculation-service:local .
```

The image listens on port `8080` and runs as an unprivileged application user.

## Runtime Configuration

The service accepts the following environment variables:

- `BIND_ADDRESS`: HTTP bind address; default `0.0.0.0`;
- `PORT`: HTTP port; default `8080`;
- `HEX_CORE_BASE_URL`: HEX Core base URL; default `http://127.0.0.1:8080`;
- `HEX_CORE_BEARER_TOKEN`: optional service-to-service token for HEX Core validation requests;
- `HTTP_TIMEOUT_SECS`: delegated HTTP timeout; default `30`;
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

## Background Data

The image contains the coauthors' general BONSAI-EF3.1 Brightway project and treats it as
immutable. Each compute request creates a temporary project copy under
`BRIGHTWAY_WORKSPACE_DIR/requests`, calculates in a separate process, and removes the copy after
completion or timeout. The workspace must be writable and must not be inside the background
source directory. The fixed base has 49,978 BONSAI activities, the EF3.1 elementary-flow
database, and 25 registered EF3.1 method entries. The example's standalone test activity is
excluded. Each request supplies its own CE-RISE foreground; the base is independent of product
type. The source archive and matrix checksums are recorded in the
[background manifest](https://codeberg.org/CE-RISE-software/see-impacts-calculation-service/src/branch/main/data/background/project.json).

The BONSAI background is licensed CC BY-SA 4.0. The computing module's source code has a separate
EUPL-1.2 license. Retain the BONSAI attribution when redistributing the image.

Concurrent compute requests have separate Brightway processes and request workspaces.
Workers default to one BLAS thread to avoid multiplying numerical-library threads across
concurrent calculations; explicit numerical-library thread settings in the environment are retained.

## Run Example

```bash
podman run --rm -p 8080:8080 \
  -e HEX_CORE_BASE_URL=http://hex-core-host:8080 \
  see-impacts-calculation-service:local
```

Replace the example HEX Core address with one reachable **from inside the container** before
calling `POST /compute`. The default `127.0.0.1` would refer to the container itself.
`BACKGROUND_PROJECT_DIR` can still select another approved project when needed.

After startup, verify both liveness and project readiness:

```bash
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/capabilities
curl -sS http://127.0.0.1:8080/methods
```

## Operational Readiness

Use `GET /health` for a lightweight liveness check. Use `GET /capabilities` as the readiness
check because it confirms that the configured Brightway project can be opened. A healthy HTTP
process is not sufficient to show that required background data has been provisioned.
