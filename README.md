# CE-RISE SEE Impacts Calculation Service

A containerized HTTP service for assessing and reporting the socio-economic and environmental
impacts of products in CE-RISE digital passport workflows.

The service is being prepared as the calculation layer behind impact assessments. It will turn
approved product information into a structured life cycle assessment result, while keeping
model validation and record management in `hex-core-service`.

For the CE-RISE solution and its components, use the
[CE-RISE Solution portal](https://solution.ce-rise.eu/) as the main entry point for human users.

## Current Status

The initial service scaffold is operational. It provides:

- `GET /health` for service identity and configuration inspection;
- `GET /capabilities` to verify that an approved Brightway 2 background project can be opened;
- `GET /openapi.json` and interactive API documentation at `/docs`;
- a reserved `POST /compute` request contract;
- a container image definition and tag-driven registry publication workflow.

The service does **not** yet execute an inventory or impact calculation. `POST /compute`
returns `501 CALCULATION_NOT_IMPLEMENTED` until the CE-RISE-to-Brightway mapping, delegated
validation orchestration, and acceptance fixture are implemented.

## How It Fits CE-RISE

The eventual calculation flow is deliberately model-driven:

1. A client submits product and life cycle inventory information for an impact assessment.
2. The service delegates validation of the selected CE-RISE models to `hex-core-service`.
3. The service maps the validated information to a temporary Brightway foreground calculation
   against an approved background project.
4. It returns a validated `integrated-lca` result record with calculation provenance.

The applicable CE-RISE model repositories are:

- [Product System](https://codeberg.org/CE-RISE-models/product-system)
- [LCI Dataset](https://codeberg.org/CE-RISE-models/lci-dataset)
- [Integrated LCA](https://codeberg.org/CE-RISE-models/integrated-lca)

## Quick Start

Create a virtual environment and install the service:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

With an approved background project available at the default ignored location, verify it:

```bash
.venv/bin/see-impacts-compatibility
.venv/bin/python -m pytest
```

Run the service locally:

```bash
. .venv/bin/activate
./scripts/run-local.sh
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/capabilities
```

For API, deployment, and local-testing guidance, use the published Pages documentation:

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

Developed by NILU (Riccardo Boero — ribo@nilu.no) within the CE-RISE project.
