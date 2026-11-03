# CE-RISE SEE Impacts Calculation Service

A containerized HTTP service for calculating environmental footprints from CE-RISE Product
System and LCI Dataset records using Brightway, the BONSAI background, and Environmental
Footprint (EF) 3.1 characterization factors.

Each successful request calculates the inventory once and returns all 25 configured
environmental indicators in one validated CE-RISE Integrated LCA object. The result includes
units, methods, the functional unit, input references, and data and software provenance.

SEE stands for socio-economic and environmental. This service provides environmental impact
calculations.

Related data models and software are described on the
[CE-RISE Solution website](https://solution.ce-rise.eu/).

## Using the Service

Submit a Product System, its LCI Dataset records, a functional unit, and their schema versions
to `POST /compute`. The service validates the records through HEX Core, assembles the foreground,
links it to the BONSAI background, and calculates the indicators. HEX Core validates the
Integrated LCA result before it is returned.

- [Compute Workflow](api-overview.md): input records, inventory links, and result structure.
- [PV Example](pv-example.md): a complete request and calculated results for a photovoltaic panel.
- [Methods and Background](scope.md): the configured EF3.1 categories, result units, and factor coverage.
- [API Reference](api-reference.md): endpoints, request fields, responses, and diagnostics.

## Deployment and Integration

[Deployment](deployment.md) covers installation, container builds, runtime settings, and service
checks. [HEX Core Integration](integration.md) describes schema validation and authentication.

## Engineering

[Architecture](architecture.md) documents foreground assembly, project isolation, and numerical
execution. [Testing](local-testing.md) covers the regression suite and Codeberg CI checks.

Funded by the European Union under Grant Agreement No. 101092281 — CE-RISE.  
Views and opinions expressed are those of the author(s) only and do not necessarily reflect those of the European Union or the granting authority (HADEA).
Neither the European Union nor the granting authority can be held responsible for them.

<a href="https://ce-rise.eu/" target="_blank" rel="noopener noreferrer">
  <img src="images/CE-RISE_logo.png" alt="CE-RISE logo" width="200"/>
</a>

© 2026 CE-RISE consortium.  
Service source licensed under the [European Union Public Licence v1.2 (EUPL-1.2)](https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12).

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

Developed by NILU (Riccardo Boero - ribo@nilu.no), Leiden University (Mintjes, B.A. (Berend) - b.a.mintjes@cml.leidenuniv.nl; Stefano Merciai - s.merciai@cml.leidenuniv.nl), and Empa (Francesco Barilli - francesco.barilli@empa.ch; Roland Hischier - roland.hischier@empa.ch) within the CE-RISE project.
