# CE-RISE SEE Impacts Calculation Service

A containerized HTTP service that calculates one environmental impact indicator for a CE-RISE
Product System. It combines the supplied LCI Dataset foreground with the configured BONSAI
background, then returns a validated Integrated LCA result or a calculation diagnostic.

For the CE-RISE solution and its components, use the
[CE-RISE Solution portal](https://solution.ce-rise.eu/) as the main entry point for human users.

## Calculate an Impact

Send `POST /compute` with five fields:

| Field | What to supply |
| --- | --- |
| `model_versions` | Product System and LCI Dataset schema versions for input validation, and the Integrated LCA schema version for output validation. These versions must be available in HEX Core. |
| `product_system` | The CE-RISE Product System record selecting the activities and declaring the reference flow. |
| `lci_datasets` | A non-empty array of CE-RISE LCI Dataset records referenced by the Product System. |
| `functional_unit` | The declared reference-flow identifier and unit, plus the positive quantity to assess. |
| `impact_method` | One complete method identifier, copied as an array from `GET /methods`. |

Product System dataset references must resolve to the supplied LCI records, selected activities
must exist in those records, and the reference flow must have the same identifier, quantity, and
unit in the Product System and its LCI Dataset. Background activity and elementary-flow links
must resolve in the configured Brightway project. Callers do not upload a Brightway project or
submit a separate mapping file.

On success, the response is one Integrated LCA object with one environmental indicator. It
contains the requested functional unit, the numeric result and unit, the selected method, input
references, and available background, factor-set, software, and timestamp provenance. A
singular calculation instead returns `status: "not_calculable"` and any activity groups it can
identify, without a score. Invalid inputs or unresolved links return `422`.

The service validates the inputs and generated result through HEX Core. Configure a reachable
`HEX_CORE_BASE_URL` with the requested model versions before calling `POST /compute`. See the
[runnable PV request](docs/api-overview.md#send-a-request) and the
[API Reference](docs/api-reference.md) for the full request and response shapes.

## Available Operations

The service provides:

- a Brightway 2.5 compatibility probe for an approved local background project;
- `GET /health` for service identity and configuration inspection;
- `GET /capabilities` for Brightway project and method availability;
- `GET /methods` for the complete set of registered impact-method identifiers;
- `POST /compute` for one environmental impact indicator in an Integrated LCA object;
- `POST /compute/diagnostics` for request-specific calculation checks, including identified
  activities when the technosphere is singular;
- `GET /openapi.json` and interactive API documentation at `/docs`;
- a container image definition and tag-driven registry publication workflow.

`POST /compute/diagnostics` accepts the same input and runs the calculation but returns only
`calculable` or `not_calculable`, never a score. For a singular technosphere, it identifies
small activity groups and whether they are reachable from the requested demand.

Each compute request runs in a separate process with a disposable copy of the prepared
background project. The source project is not changed. The local test suite exercises the full
workflow with a PV Product System and LCI Dataset against the bundled BONSAI background.

## Background Access

The compatibility probe checks that Brightway can read the configured background project and
load a registered impact method. It does not calculate an impact or validate foreground records.
The full PV calculation test runs locally; Codeberg CI validates the PV input and output records
against the published data models without running the calculation. See
[Local Testing](docs/local-testing.md).

## Use Locally

Create a virtual environment and install the service:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m pytest
```

To run the HTTP service locally, prepare the Brightway project from the bundled seed and
BONSAI IO release:

```bash
mkdir -p data/background/projects
tar -xzf data/background/cerise_bonsai.tar.gz -C data/background/projects
.venv/bin/python -m see_impacts_calculation_service.import_bonsai \
  data/background/bonsai-3.8-beta2 \
  data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9 \
  --project-name cerise_bonsai
.venv/bin/see-impacts-compatibility
```

Start the HTTP service. Replace the example HEX Core address with one reachable from this
machine; `/compute` uses it for input and output validation:

```bash
HEX_CORE_BASE_URL=http://hex-core-host:8080 \
  .venv/bin/python -m uvicorn see_impacts_calculation_service.app:app --host 127.0.0.1 --port 8080
```

In another terminal, check it:

```bash
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/capabilities
curl -sS http://127.0.0.1:8080/methods
```

`GET /health` confirms the process is running. `GET /capabilities` opens the configured
background project and lists its databases and sample methods. `GET /methods` lists every
registered method identifier.

With HEX Core reachable and a request JSON document prepared as shown in the
[PV example](docs/api-overview.md#send-a-request), call:

```bash
curl --fail-with-body --silent --show-error \
  -H 'Content-Type: application/json' \
  --data-binary @compute-request.json \
  http://127.0.0.1:8080/compute
```

## Documentation

The published Pages site contains endpoint, deployment, and local-testing details:

- [Documentation Home](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/)
- [API Reference](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/api-reference.html)
- [Deployment](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/deployment.html)
- [Local Testing](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/local-testing.html)

## Background Data

The repository includes a seed Brightway project with biosphere flows and impact methods,
plus the six-file [BONSAI 3.8-beta2 (bw) IO release](https://doi.org/10.5281/zenodo.15421526).
The build imports that release as the `bonsai` database. The default Brightway project is
`data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9`.
The expanded local project remains untracked. Use a distinct writable
`BRIGHTWAY_WORKSPACE_DIR` for Brightway state. See
[Background Data](data/background/README.md) for checksums and attribution. The pinned IO
release is published under CC BY-SA 4.0; the computing module's source code is licensed
separately under EUPL-1.2.

## Container Releases

Pushing a `v*.*.*` tag to the canonical Codeberg repository publishes a versioned image at:

```text
$REGISTRY_HOST/$REGISTRY_NAMESPACE/see-impacts-calculation:<tag>
```

The same release image is promoted to `latest`. Before the first release, configure the
repository-level Forgejo variables `REGISTRY_HOST` and `REGISTRY_NAMESPACE`, plus the
`REGISTRY_USERNAME` and `REGISTRY_PASSWORD` secrets.

The released image includes the BONSAI background project from this repository. See the
[deployment documentation](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/deployment.html)
for a container run example.


## License

Licensed under the [European Union Public Licence v1.2 (EUPL-1.2)](LICENSE).

## Contributing

This repository is maintained on [Codeberg](https://codeberg.org/CE-RISE-software/see-impacts-calculation-service) - the canonical source of truth. The GitHub repository is a read mirror used for release archival and Zenodo integration. Issues and pull requests should be opened on Codeberg.

---

<a href="https://europa.eu" target="_blank" rel="noopener noreferrer">
  <img src="https://ce-rise.eu/wp-content/uploads/2023/01/EN-Funded-by-the-EU-PANTONE-e1663585234561-1-1.png" alt="EU emblem" width="200"/>
</a>

Funded by the European Union under Grant Agreement No. 101092281 — CE-RISE.  
Views and opinions expressed are those of the author(s) only and do not necessarily reflect those of the European Union or the granting authority (HADEA).
Neither the European Union nor the granting authority can be held responsible for them.

© 2026 CE-RISE consortium.  
Licensed under the [European Union Public Licence v1.2 (EUPL-1.2)](LICENSE).  
Attribution: CE-RISE project (Grant Agreement No. 101092281) and the individual authors/partners as indicated.

<a href="https://www.nilu.com" target="_blank" rel="noopener noreferrer">
  <img src="https://nilu.no/wp-content/uploads/2023/12/nilu-logo-seagreen-rgb-300px.png" alt="NILU logo" height="20"/>
</a>
<a href="https://www.universiteitleiden.nl" target="_blank" rel="noopener noreferrer">
  <img src="https://upload.wikimedia.org/wikipedia/commons/b/b0/UniversiteitLeidenLogo.svg" alt="Leiden University logo" height="30"/>
</a>
<a href="https://www.empa.ch" target="_blank" rel="noopener noreferrer">
  <img src="https://www.empa.ch/image/company_logo?img_id=31464838&t=1762532293211" alt="Empa logo" height="30"/>
</a>

Developed by NILU (Riccardo Boero - ribo@nilu.no), Leiden University (Mintjes, B.A. (Berend) - b.a.mintjes@cml.leidenuniv.nl), and Empa (Francesco Barilli - francesco.barilli@empa.ch; Roland Hischier - roland.hischier@empa.ch) within the CE-RISE project.
