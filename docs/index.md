# CE-RISE SEE Impacts Calculation Service

This site documents the CE-RISE SEE impacts calculation service. SEE stands for socio-economic
and environmental impacts.

The [CE-RISE Solution portal](https://solution.ce-rise.eu/) is the main entry point for human
users exploring the wider solution and its components.

## Available Service Functions

The service provides Brightway project compatibility checks and an HTTP service boundary:

- `GET /health` reports the service identity and configuration;
- `GET /capabilities` opens the configured Brightway project and reports databases and methods;
- `GET /openapi.json` and `GET /docs` provide the machine-readable and interactive API;
- `see-impacts-compatibility` runs the same Brightway project check from the command line;
- the container image runs the same HTTP service with externally mounted background data.

## Use the Service

Install and inspect the local project:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/see-impacts-compatibility
```

Start the HTTP service with the virtual environment active:

```bash
./scripts/run-local.sh
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/capabilities
```

`POST /compute` is documented so consumers can inspect its JSON schema. It returns
`501 CALCULATION_NOT_IMPLEMENTED`; it does not provide a calculation operation.

## Documentation Structure

- [Architecture](architecture.md): active service components and data handling
- [API Overview](api-overview.md): available endpoints and compute request schema
- [API Reference](api-reference.md): endpoint-level request, response, and error behavior
- [Deployment](deployment.md): container image, configuration, and background provisioning
- [Local Testing](local-testing.md): probe, test, and local container workflows
- [HEX Core Status](integration.md): available configuration and client boundary
- [Project Scope](scope.md): available service scope and exclusions

---




---

Funded by the European Union under Grant Agreement No. 101092281 — CE-RISE.  
Views and opinions expressed are those of the author(s) only and do not necessarily reflect those of the European Union or the granting authority (HADEA).
Neither the European Union nor the granting authority can be held responsible for them.

<a href="https://ce-rise.eu/" target="_blank" rel="noopener noreferrer">
  <img src="images/CE-RISE_logo.png" alt="CE-RISE logo" width="200"/>
</a>

© 2026 CE-RISE consortium.  
Licensed under the [European Union Public Licence v1.2 (EUPL-1.2)](https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12).  
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
