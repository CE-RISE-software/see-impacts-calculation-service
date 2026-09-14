# Deployment

## Service Form

This project is deployed as a containerized HTTP service. The repository includes a `Dockerfile`
and `.dockerignore`; the background dataset is deliberately excluded from the build context and
the resulting image.

## Image Publication

Pushing a `v*.*.*` tag to the canonical Codeberg repository triggers the Forgejo release
workflow. It builds and publishes:

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
- `HTTP_TIMEOUT_SECS`: delegated HTTP timeout; default `30`;
- `BACKGROUND_PROJECT_DIR`: approved Brightway project directory; default
  `data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9`;
- `BACKGROUND_PROJECT_NAME`: expected project name from `.project-name.json`; default
  `cerise_bonsai`;
- `BRIGHTWAY_WORKSPACE_DIR`: writable Brightway registry workspace; default
  `runtime/brightway` locally and `/var/lib/see-impacts/brightway` in the container image.

`HEX_CORE_BASE_URL` and `HTTP_TIMEOUT_SECS` are accepted runtime settings. The available HTTP
endpoints do not make an outbound HEX Core request.

## Background Data Provisioning

The image contains code and dependencies only. Background data must be provided separately and
treated as immutable. The service creates Brightway registry state in
`BRIGHTWAY_WORKSPACE_DIR`; this path must be writable and must not be the background source
directory.

Each concurrently running worker should use its own writable Brightway workspace. This avoids
concurrent mutation of Brightway's process-global project registry.

## Run Example

From a local checkout where the approved project is stored under the ignored
`data/background` directory:

```bash
podman run --rm -p 8080:8080 \
  -e BACKGROUND_PROJECT_DIR=/data/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9 \
  -e BACKGROUND_PROJECT_NAME=cerise_bonsai \
  -e BRIGHTWAY_WORKSPACE_DIR=/var/lib/see-impacts/brightway \
  -v "$PWD/data/background:/data:ro,Z" \
  see-impacts-calculation-service:local
```

The `:Z` suffix is appropriate for Podman on SELinux-enabled hosts. Use the equivalent
read-only volume syntax required by the target container runtime.

After startup, verify both liveness and project readiness:

```bash
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/capabilities
```

## Operational Readiness

Use `GET /health` for a lightweight liveness check. Use `GET /capabilities` as the readiness
check because it confirms that the configured Brightway project can be opened. A healthy HTTP
process is not sufficient to show that required background data has been provisioned.
