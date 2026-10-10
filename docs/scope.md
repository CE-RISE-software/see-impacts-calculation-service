# Project Scope

## Available Scope

The repository provides a containerized Python HTTP service for calculating one environmental
impact indicator from CE-RISE Product System and LCI Dataset inputs. The usable operations
include the command-line compatibility probe, health, capability, and method-discovery
endpoints, compute and diagnostic endpoints, OpenAPI document, and container release workflow.
Input and output model validation is delegated to HEX Core.

Background source data remains local and read-only. Brightway registry state uses a separate
writable workspace. The API and operating guidance are published through the repository's
Codeberg Pages site.

## Calculation and Access Check

`POST /compute` accepts CE-RISE Product System and LCI Dataset objects, a requested functional
unit, and an impact method. A successful calculation returns a HEX Core-validated Integrated
LCA object containing one environmental indicator. A singular matrix returns a structured
diagnostic without a score. `POST /compute/diagnostics` makes the same calculation attempt
but does not publish the score or result object.

The background check verifies read access to the imported BONSAI project through
Brightway: database registration, one record and its exchanges per database, processed
datapackages, and one registered impact method's factors. It does not prove that a particular
foreground request will calculate. The prepared project is accessed read-only at runtime.

Foreground assembly is available as an internal module. It constructs selected activities,
product outputs, and exact internal input links from CE-RISE records and identifies the reference
output. It retains external background inputs and elementary flows for the calculation runner.
The HTTP endpoints use transient datapackages rather than writing a foreground database.

An internal calculation path combines the foreground with background and impact-method
datapackages in memory. It uses exact background activity and biosphere flow identifiers and
converts compatible units. The normal test suite builds a fresh BONSAI project and verifies a
PV request through input validation, calculation, and Integrated LCA output validation. This
does not guarantee that every foreground request can be solved.

## Not Provided

- a guarantee that every request is calculable with the supplied background;
- uncertainty quantification, sensitivity analysis, or a multi-indicator assessment;
- a Brightway database-management API;
- a general-purpose LCA application, CLI, or notebook interface.
