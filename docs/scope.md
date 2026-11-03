# Methods and Background

The service calculates environmental impacts from a CE-RISE Product System, its referenced LCI
Dataset records, and a functional unit. HEX Core validates the inputs and result against the
data-model versions specified in the request.

The bundled BONSAI-EF3.1 background provides 25 methods with fixed characterization factors and
elementary-flow links. Every request uses this shared configuration to calculate all indicators
from one inventory.

Calculations are independent of product category. The supplied inventory defines the foreground,
and its external activity and elementary-flow identifiers link it to the background.

## Background Inventory

The bundled Brightway project contains:

| Database | Contents | Records |
| --- | --- | --- |
| `BONSAI` | Background activities used for external inventory links. | 49,978 |
| `ef31_biosphere` | EF3.1 elementary flows used for emissions and resource exchanges. | 93,993 |
| `BONSAI biosphere` | Additional elementary flows referenced by the background. | 7 |

The [background manifest](https://codeberg.org/CE-RISE-software/see-impacts-calculation-service/src/branch/main/data/background/project.json)
identifies the source archive, database counts, method metadata, and checksums. The background
data are licensed CC BY-SA 4.0; the service source code is licensed separately under EUPL-1.2.

## Characterization and Results

The BONSAI-EF3.1 project has 25 registered method entries that
include impact categories and subcategories. Each request solves the inventory once, applies
each method to that same inventory, and returns all 25 characterized indicators in one Integrated
LCA object. Each indicator has its own unit, method version, and factor-set reference.
Characterization factors are part of the deployed background configuration; changing them
requires deploying an updated project.

All methods belong to the EF3.1 family. The table lists their registered categories and result
units; `GET /methods` returns the complete identifiers used in the output:

| Category or Subcategory | Result Unit |
| --- | --- |
| Acidification | `mol H+-Eq` |
| Climate change | `kg CO2-Eq` |
| Climate change-Biogenic | `kg CO2-Eq` |
| Climate change-Fossil | `kg CO2-Eq` |
| Climate change-Land use and land use change | `kg CO2-Eq` |
| EF-particulate matter | `disease incidence` |
| Ecotoxicity, freshwater | `CTUe` |
| Ecotoxicity, freshwater_inorganics | `CTUe` |
| Ecotoxicity, freshwater_organics | `CTUe` |
| Eutrophication marine | `kg N-Eq` |
| Eutrophication, freshwater | `kg P-Eq` |
| Eutrophication, terrestrial | `mol N-Eq` |
| Human toxicity, cancer | `CTUh` |
| Human toxicity, cancer_inorganics | `CTUh` |
| Human toxicity, cancer_organics | `CTUh` |
| Human toxicity, non-cancer | `CTUh` |
| Human toxicity, non-cancer_inorganics | `CTUh` |
| Human toxicity, non-cancer_organics | `CTUh` |
| Ionising radiation, human health | `kBq U235-Eq` |
| Land use | `pt` |
| Ozone depletion | `kg CFC-11-Eq` |
| Photochemical ozone formation - human health | `kg NMVOC-Eq` |
| Resource use, fossils | `MJ` |
| Resource use, minerals and metals | `kg Sb-Eq` |
| Water use | `m3 world Eq deprived` |

The results are characterized values in each indicator's unit, not a single weighted score.
Categories and their subcategories are reported separately and overlap; interpret them
individually rather than summing them.

## Flow Coverage and Geography

External background activity references resolve in `BONSAI`; elementary-flow identifiers
resolve in `ef31_biosphere`. Compatible units are converted. An unknown identifier is an error.
A resolved elementary flow
with no factor in a particular method contributes zero to that indicator, while remaining part
of the calculated inventory.

The calculation uses each method's global (`GLO`) factors, as defined by the
[Brightway LCIA implementation](https://docs.brightway.dev/en/latest/_modules/bw2calc/lca.html#LCA.load_lcia_data).
Regional factor records remain in the project but are excluded from the calculation. Geographic
background differences enter through the selected BONSAI activities. Foreground location
metadata does not select country-specific characterization factors.

## Reproducing and Comparing Results

To reproduce a result, retain the input records, functional unit, background snapshot, and
configured methods and factor sets. Comparisons between alternatives require compatible
functional units and study boundaries and the same background and method setup. Replacing the
background or factors can change scores even with an unchanged foreground. The Integrated LCA output
records the available background version and source-archive identifier, plus each indicator's
method version and factor-set reference for this purpose.
