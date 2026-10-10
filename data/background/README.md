# BONSAI Background

`cerise_bonsai.tar.gz` is the seed Brightway project containing `biosphere3` and registered
impact methods. It expands to
`projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9`.

SHA-256: `58afc02d88e3ad47334c210bbeacdaa3f950954338629af7a857f34909f1fe1f`

`bonsai-3.8-beta2/` contains the six published files from
[EXIOBASE-hybrid - Consequential System, version 3.8-beta2 (bw)](https://doi.org/10.5281/zenodo.15421526).
The image build verifies their SHA-256 hashes, imports them as the `bonsai` database using the
commit pinned in `requirements-background-build.txt`, and removes the source files from the
runtime image. The importer aliases the published `index_table_hiot.gzip` to the filename it
expects; no source table is modified. The import follows the
[published Brightway example](https://github.com/Depart-de-Sentier/brightcon-2024-material/blob/main/talks/Wednesday/io_bonsai_importer/io_bonsai_import.ipynb).
The prepared project has 34,567 BONSAI activities.

The Zenodo release is licensed CC BY-SA 4.0. Attribute its creators and release when
redistributing the data or image. The computing module's source code is licensed separately
under EUPL-1.2; that software license does not replace the data license.
