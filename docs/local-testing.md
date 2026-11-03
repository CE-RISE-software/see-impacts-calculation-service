# Testing

The test suite covers input and output validation, foreground construction, numerical
calculations, diagnostics, and request isolation. Service setup is documented under
[Deployment](deployment.md).

## Setup

Use Python 3.11 or 3.12 to create a virtual environment and install the service with its test
dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-test.txt
```

## Tests

```bash
.venv/bin/python -m pytest
```

The PV integration test extracts a fresh copy of the bundled background and submits the example
records to `POST /compute`. It compares all 25 calculated indicators with the saved result in
`tests/fixtures/pv/integrated-lca.json`. Other numerical tests use a small synthetic background
to check known results, unit conversion, singularity diagnostics, concurrent requests, and one
inventory solve per request.

Schema validation uses the latest published Product System, LCI Dataset, and Integrated LCA
schemas from Codeberg. These checks require network access to Codeberg and run without a live
HEX Core service.

## Continuous Integration

Codeberg runs the core tests on `codeberg-medium` and PV record validation on `codeberg-small`
for pushes, pull requests, and releases. The PV CI job validates the example inputs and the
complete saved output against the published schemas. It does not run the full numerical PV
calculation.

Run the same record-validation check locally:

```bash
.venv/bin/python -m pytest -q tests/test_pv_integration.py::test_pv_records_against_published_models
```

## Background Verification

The compatibility command checks that Brightway can read the background and its registered
impact methods. Prepare the bundled project before running the check:

```bash
.venv/bin/python -m see_impacts_calculation_service.prepare_background \
  data/background/cerise_bonsai.tar.gz data/background/projects \
  --project-name cerise_bonsai
.venv/bin/see-impacts-compatibility
```

The default background project location is
`data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9`.
`BACKGROUND_PROJECT_DIR` selects a different project location. The separate
`BRIGHTWAY_WORKSPACE_DIR` holds Brightway's writable project registry and defaults to
`runtime/brightway`.

The command reports database and method metadata as JSON. It reads a record and its exchanges
from each database, opens the processed datapackages, and loads factors from a registered
method. This verifies data access; numerical calculations are covered by the integration tests.

## Container Smoke Test

Build the image locally:

```bash
podman build -t see-impacts-calculation-service:local .
```

Run it with the included BONSAI background project:

```bash
podman run --rm -p 8081:8080 \
  see-impacts-calculation-service:local
```

In a second terminal, check the background:

```bash
curl --fail-with-body -sS http://127.0.0.1:8081/capabilities
```

This check reads the bundled background and reports its databases and methods. It does not
require HEX Core. The [Compute Workflow](api-overview.md) covers calculation requests with
input and output validation; the [PV Example](pv-example.md) provides a complete request.
