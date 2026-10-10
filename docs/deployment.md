# Deployment

## Service Form

This project is deployed as a containerized HTTP service. The `Dockerfile` extracts the seed
Brightway project, imports the bundled BONSAI 3.8-beta2 IO release into it, and verifies that
Brightway can read the result. A failed import or verification stops the image build.

## Image Publication

Pushing a `v*.*.*` tag to the canonical Codeberg repository triggers the Forgejo release
workflow. The test suite must pass before it builds and publishes:

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
  default `bonsai`;
- `BIOSPHERE_DATABASE_NAME`: Brightway database used for elementary flows; default `biosphere3`;
- `BRIGHTWAY_WORKSPACE_DIR`: writable Brightway registry workspace; default
  `runtime/brightway` locally and `/var/lib/see-impacts/brightway` in the container image.
- `CALCULATION_TIMEOUT_SECS`: maximum time for one isolated calculation; default `900`.

`POST /compute` and `POST /compute/diagnostics` call HEX Core to retrieve each requested
input model's JSON Schema and validate the Product System and LCI Dataset objects.
`POST /compute` also validates the generated Integrated LCA object through HEX Core. Provision
a reachable HEX Core registry
and an appropriate service identity before using that endpoint. The bearer token is never
returned by `GET /health`.

## Background Data

The image contains a prepared BONSAI 3.8-beta2 Brightway project and treats it as
immutable. Each compute request creates a temporary project copy under
`BRIGHTWAY_WORKSPACE_DIR/requests`, calculates in a separate process, and removes the copy after
completion or timeout. The workspace must be writable and must not be inside the background
source directory. The build uses the pinned
[BONSAI Brightway importer](https://github.com/mfastudillo/brightway2-io/blob/9f62977cf83ffa45453f410a3bdbc19f38b03811/bw2io/importers/bonsai.py)
and the [public IO release](https://doi.org/10.5281/zenodo.15421526). The six source files
are not carried into the runtime image.

This IO release is licensed CC BY-SA 4.0. The computing module's source code has a separate
EUPL-1.2 license. Attribute the BONSAI release when redistributing the image.

Concurrent compute requests have separate Brightway processes and request workspaces.

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
