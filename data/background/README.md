# BONSAI-EF3.1 Background

`cerise_bonsai.tar.gz` contains the general BONSAI-EF3.1 Brightway project supplied by the
service coauthors. It expands to
`projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9` and includes:

- `BONSAI`: 49,978 background activities;
- `ef31_biosphere`: 93,993 Environmental Footprint elementary flows;
- `BONSAI biosphere`: seven additional background flows;
- 25 registered EF3.1 method entries, including categories and subcategories, with their
  characterization factors and geographic identifiers.

The archive is independent of product type. Foreground activities come from each calculation
request. The source project's standalone `test_activities` database and its user-interface
caches are excluded. All background and characterization datapackages are preserved byte for
byte. Intermediate method records are restored from those datapackages so Brightway can also
load and inspect the factors. Two reversed result-unit labels are corrected: fossil resource
use is `MJ`; mineral and metal resource use is `kg Sb-Eq`.

[project.json](project.json) records the source filename, source and bundled archive SHA-256
checksums, database counts, all method identifiers, and original matrix checksums. The source
is `BONSAI_EF3.1_Brightway25_Project.gz`, SHA-256
`339e6e3199bd13c7ab5f1948bfd9626f033668dac4bfad4705d17d8c52993a0b`.

The build extracts and verifies this linked project directly. It does not re-import a different
BONSAI release or reconstruct the elementary-flow matching. Each request uses a disposable copy
of the prepared project, with its own foreground. Factor tables are fixed service configuration.

Calculations use the selected method's global factors through Brightway's standard LCIA path.
The regional factor records remain in the archive. Runtime geographic treatment and factor
coverage are described under
[Characterization and Results](../../docs/scope.md#characterization-and-results).

BONSAI background data retain their CC BY-SA 4.0 license. Attribute the BONSAI data creators and
the CE-RISE contributors to the supplied configuration when redistributing the archive or image.
The method is the European Commission/JRC
[Environmental Footprint 3.1](https://eplca.jrc.ec.europa.eu/LCDN/developerEF.html).
The service source is licensed separately under EUPL-1.2.
