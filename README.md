# CE-RISE SEE Impacts Calculation Service

A containerized HTTP service that calculates environmental impacts from CE-RISE Product System
and LCI Dataset objects and returns HEX Core-validated Integrated LCA results when the
calculation succeeds. It also inspects an approved Brightway 2.5 background project and
diagnoses requests that cannot be solved.

For the CE-RISE solution and its components, use the
[CE-RISE Solution portal](https://solution.ce-rise.eu/) as the main entry point for human users.

## Available Now

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

`POST /compute` requires a functional unit and a registered impact method. It delegates
Product System and LCI Dataset conformance checks to HEX Core, assembles the foreground,
calculates an impact score, builds an Integrated LCA object, and validates that object through
HEX Core before returning it. Invalid inputs or unresolved calculation links return `422`;
a singular technosphere returns a structured `not_calculable` diagnostic instead of a score.
HEX Core must have the requested JSON Schema artifacts and be reachable at `HEX_CORE_BASE_URL`;
set `HEX_CORE_BEARER_TOKEN` when it requires a service-to-service bearer token.

`POST /compute/diagnostics` accepts the same request and attempts an in-memory calculation.
It reports `calculable` or `not_calculable`, never a score. For a singular
technosphere, it reports small identified activity groups and whether they are reachable from
the requested demand. These findings do not establish that foreground detail is missing and
are not an exhaustive diagnosis.

The published compute schema uses CE-RISE data plus the requested Brightway impact method:
a Product System object and LCI Dataset object(s) are inputs, while the selected Integrated LCA
version identifies the result object. The semantic content of the input objects is the basis
for the internal Brightway calculation.
Brightway is an implementation detail; there is no separate mapping object or API for callers to
provide.

Successful results record the configured background project and database identifiers, the
service version, and the `bw2data` and `bw2calc` versions used for the calculation. The
background identifiers are not a content checksum or dataset version.

The internal foreground builder assembles selected activities, product outputs, and internal
input links from those objects. External background inputs and elementary flows are retained for
the calculation stage. An internal runner links exact background and biosphere identifiers,
converts compatible units, and combines the foreground with Brightway datapackages in memory.
It does not write to the BONSAI archive. The supplied BONSAI snapshot currently yields a
singular technosphere for the tested calculation, so no numerical result is claimed for it.

## Background Access

The compatibility probe verifies that Brightway can open the supplied BONSAI data, read a
record and its exchanges from each bundled database, open each processed datapackage, and load
factors from a registered impact method. It does not calculate impacts or validate a foreground
inventory. See [Local Testing](docs/local-testing.md) for the optional test against the local
archive.

## Use Locally

Create a virtual environment and install the service:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

With the approved Brightway project at `data/background`, verify it:

```bash
.venv/bin/see-impacts-compatibility
.venv/bin/python -m pytest
```

Start the HTTP service:

```bash
. .venv/bin/activate
./scripts/run-local.sh
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/capabilities
curl -sS http://127.0.0.1:8080/methods
```

`GET /health` confirms the process is running. `GET /capabilities` opens the configured
background project and lists its databases and sample methods. `GET /methods` lists every
registered method identifier.

## Documentation

The published Pages site contains endpoint, deployment, and local-testing details:

- [Documentation Home](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/)
- [API Reference](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/api-reference.html)
- [Deployment](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/deployment.html)
- [Local Testing](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/local-testing.html)

## Background Data

The default local Brightway project is
`data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9`. It is excluded from
Git and container images. Every deployment must separately approve and provision its background
data at `BACKGROUND_PROJECT_DIR`, with a distinct writable
`BRIGHTWAY_WORKSPACE_DIR` for Brightway state.

## Container Releases

Pushing a `v*.*.*` tag to the canonical Codeberg repository publishes a versioned image at:

```text
$REGISTRY_HOST/$REGISTRY_NAMESPACE/see-impacts-calculation:<tag>
```

The same release image is promoted to `latest`. Before the first release, configure the
repository-level Forgejo variables `REGISTRY_HOST` and `REGISTRY_NAMESPACE`, plus the
`REGISTRY_USERNAME` and `REGISTRY_PASSWORD` secrets.

The released image never includes background data. See the [deployment documentation](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/deployment.html) for a container run example.


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
