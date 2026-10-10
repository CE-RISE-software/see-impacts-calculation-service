# Service Scope

The service calculates one environmental impact indicator per request for a CE-RISE Product
System. A request supplies the Product System, its referenced LCI Dataset records, a quantity
for the declared reference flow, and an impact method registered in the configured Brightway
project. The container includes a BONSAI background project; another prepared project can be
configured for deployment.

Applicability depends on the supplied foreground and on whether its background activity and
elementary-flow references resolve in that project. It is not defined by a list of supported
product categories. The service uses explicit links from the CE-RISE records and does not guess
missing providers.

## Validation and Calculation

Both compute endpoints validate the Product System and LCI Dataset records against the requested
model versions through HEX Core. The service assembles their selected activities and exchanges,
converts compatible units, and calculates in a disposable copy of the prepared background. The
source background is not modified. Invalid records, unresolved links, and incompatible units
return errors rather than a result.

## Results and Diagnostics

`POST /compute` returns an Integrated LCA object with one environmental indicator, the assessed
functional unit, method, and available data and software provenance. HEX Core validates the
generated object against the requested Integrated LCA model version before it is returned.

`POST /compute/diagnostics` attempts the same calculation but returns only whether it is
calculable. If the technosphere is singular, either endpoint returns a diagnostic with any
involved activity groups the service can identify, without an impact score.

The current calculation covers the environmental dimension of SEE impacts. Results are returned
to the caller; this service does not store them. See the [Compute Workflow](api-overview.md) for
the request and result, and [Local Testing](local-testing.md) for the tested PV example.
