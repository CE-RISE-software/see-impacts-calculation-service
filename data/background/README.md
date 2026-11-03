# BONSAI-EF3.1 Background

`cerise_bonsai.tar.gz` contains the BONSAI-EF3.1 Brightway background. It expands to
`projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9` and includes:

- `BONSAI`: 49,978 background activities;
- `ef31_biosphere`: 93,993 Environmental Footprint elementary flows;
- `BONSAI biosphere`: seven additional background flows;
- 25 registered EF3.1 method entries, including categories and subcategories, with their
  characterization factors and geographic identifiers.

The background is shared by all product types. Foreground activities come from each calculation
request. Each request calculates the inventory once and applies all 25 methods using their
global factors, returning all indicators in one Integrated LCA object. Geographic treatment and
factor coverage are described under
[Characterization and Results](../../docs/scope.md#characterization-and-results).

## Source and Archive Preparation

[project.json](project.json) records the source filename, source and bundled archive SHA-256
checksums, database counts, all method identifiers, and original matrix checksums. The source
is `BONSAI_EF3.1_Brightway25_Project.gz`, SHA-256
`339e6e3199bd13c7ab5f1948bfd9626f033668dac4bfad4705d17d8c52993a0b`.

The archive excludes the source project's `test_activities` database and user-interface caches.
Background and characterization datapackages are preserved byte for byte. Method records mirror
the processed factor datapackages. Result-unit metadata use `MJ` for fossil resources and
`kg Sb-Eq` for mineral and metal resources, correcting the two reversed labels in the source.

The container build extracts and verifies the archive. Each calculation uses a temporary copy
of the project, with its own foreground. Activity links, factor tables, and regional factor
records are retained in the bundled project.

## License and Attribution

BONSAI background data retain their CC BY-SA 4.0 license. Attribute the BONSAI data creators and
the CE-RISE contributors to the supplied configuration when redistributing the archive or image.
Characterization uses the European Commission/JRC
[Environmental Footprint 3.1](https://eplca.jrc.ec.europa.eu/LCDN/developerEF.html).
The service source is licensed separately under EUPL-1.2.
