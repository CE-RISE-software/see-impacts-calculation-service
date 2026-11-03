# Service Scope

The service calculates environmental impact indicators for a CE-RISE Product
System. A request supplies the Product System, its referenced LCI Dataset records, a quantity
for the declared reference flow, and input and output model versions. The container includes
the coauthors' BONSAI-EF3.1 background project with 25 registered
method entries. Its characterization factors and elementary-flow links are fixed configuration
shared by all products. Every request calculates all configured indicators from one inventory.
Another prepared project can be configured for deployment.

Applicability depends on the supplied foreground and on whether its background activity and
elementary-flow references resolve in that project. It is not defined by a list of supported
product categories. The service uses explicit links from the CE-RISE records and does not guess
missing providers.

## Characterization and Results

The adopted configuration is the supplied BONSAI-EF3.1 project. Its 25 registered entries
include impact categories and subcategories. Each request solves the inventory once, applies
each method to that same inventory, and returns all 25 characterized indicators in one Integrated
LCA object. Each indicator has its own unit, method version, and factor-set reference.
The service applies the stored factor values;
changing them requires preparing and deploying an updated background project.

The foreground must reference activities in `BONSAI` and elementary flows in `ef31_biosphere`.
Compatible units are converted. An unknown identifier is an error. A resolved elementary flow
with no factor in a particular method contributes zero to that indicator, while remaining part
of the calculated inventory.

The calculation uses each method's global (`GLO`) factors. Regional factors are retained
in the supplied project, but Brightway's standard LCIA calculation filters them out. Geographic
background differences enter through the selected BONSAI activities; foreground location
metadata does not automatically select country-specific characterization factors. This follows
the [Brightway LCIA implementation](https://docs.brightway.dev/en/latest/_modules/bw2calc/lca.html#LCA.load_lcia_data).

To reproduce a result, retain the input records, functional unit, background snapshot, and
configured methods and factor sets. Comparisons between alternatives require compatible functional
units and study boundaries and the same background and method setup. Replacing the background
or factors can change scores even with an unchanged foreground. The Integrated LCA output
records the available background version and source-archive identifier, plus each indicator's
method version and factor-set reference for this purpose.

## Validation and Calculation

Both compute endpoints validate the Product System and LCI Dataset records against the requested
model versions through HEX Core. The service assembles their selected activities and exchanges,
converts compatible units, and calculates in a disposable copy of the prepared background. The
source background is not modified. Invalid records, unresolved links, and incompatible units
return errors rather than a result.

## Results and Diagnostics

`POST /compute` returns one Integrated LCA object with all environmental indicators, the assessed
functional unit, each method's provenance, and available data and software provenance. HEX Core
validates the generated object against the requested Integrated LCA model version before it is returned.

`POST /compute/diagnostics` attempts the same calculation but returns only whether it is
calculable. If the technosphere is singular, either endpoint returns a diagnostic with any
involved activity groups the service can identify, without an impact score.

The current calculation covers the environmental dimension of SEE impacts. Results are returned
to the caller; this service does not store them. See the [Compute Workflow](api-overview.md) for
the request and result, and [Local Testing](local-testing.md) for the tested PV example.
