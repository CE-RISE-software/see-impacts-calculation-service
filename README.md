# CE-RISE SEE Impacts Calculation Service

A containerized HTTP service for calculating environmental footprints from CE-RISE Product
System and LCI Dataset records using Brightway, the BONSAI background, and Environmental
Footprint (EF) 3.1 characterization factors.

The service:

- validates the input records through HEX Core;
- calculates the inventory once and applies all 25 configured EF3.1 methods;
- returns one CE-RISE Integrated LCA object containing all indicators, units, methods, and
  calculation provenance;
- reports validation failures, unresolved inventory links, and singular calculations.

Related data models and software are described on the
[CE-RISE Solution website](https://solution.ce-rise.eu/).

---

## How to Use the Service

The service works alongside HEX Core for input and output validation.

1. Submit a Product System, its referenced LCI Dataset records, a functional unit, and the
   input and output schema versions to `POST /compute`.
2. The service validates the records and builds the foreground from their activities and flows.
3. Brightway combines the foreground with the bundled BONSAI background, solves the inventory
   once, and calculates all 25 environmental indicators.
4. The service validates and returns the complete Integrated LCA object.

The repository includes a photovoltaic (PV) example with
[Product System](tests/fixtures/pv/product-system.json),
[LCI Dataset](tests/fixtures/pv/lci-dataset.json), and
[Integrated LCA result](tests/fixtures/pv/integrated-lca.json) records.

API, deployment, and testing instructions are available in the documentation:

- [Documentation Home](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/)
- [API Reference](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/api-reference.html)
- [Deployment](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/deployment.html)
- [Local Testing](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/local-testing.html)

## Background Data

The bundled BONSAI-EF3.1 background contains 49,978 BONSAI activities, 93,993 EF elementary
flows, and 25 EF3.1 method entries covering impact categories and subcategories. Its activity
links and characterization factors are fixed service configuration, shared by all product
systems. Each calculation uses a separate temporary project with the supplied foreground.

See [Background Data](data/background/README.md) for source identification, checksums, and
attribution, and [Characterization and Results](docs/scope.md#characterization-and-results)
for factor coverage and geographic treatment.

## License

The service source is licensed under the [European Union Public Licence v1.2 (EUPL-1.2)](LICENSE).
The bundled BONSAI files retain the CC BY-SA 4.0 license described under Background Data.

## Contributing

This repository is maintained on
[Codeberg](https://codeberg.org/CE-RISE-software/see-impacts-calculation-service).
The GitHub mirror supports release archival and Zenodo integration. Open issues and pull
requests on Codeberg.

---

<a href="https://europa.eu" target="_blank" rel="noopener noreferrer">
  <img src="https://ce-rise.eu/wp-content/uploads/2023/01/EN-Funded-by-the-EU-PANTONE-e1663585234561-1-1.png" alt="EU emblem" width="200"/>
</a>

Funded by the European Union under Grant Agreement No. 101092281 — CE-RISE.  
Views and opinions expressed are those of the author(s) only and do not necessarily reflect those of the European Union or the granting authority (HADEA).
Neither the European Union nor the granting authority can be held responsible for them.

© 2026 CE-RISE consortium.  
Service source licensed under the [European Union Public Licence v1.2 (EUPL-1.2)](LICENSE).

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
