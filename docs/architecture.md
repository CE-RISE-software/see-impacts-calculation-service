# Architecture

## Available Components

The service is a containerized Python HTTP application with these active components:

- `app.py` exposes health, capability, compute, diagnostic, OpenAPI, and API-documentation endpoints;
- `compatibility.py` opens the supplied Brightway project and reports its databases and methods;
- `import_bonsai.py` verifies and imports the pinned BONSAI IO release during image preparation;
- `brightway_runner.py` runs a single internal Brightway 2.5 LCIA and rejects non-finite scores;
- `config.py` reads HTTP, background-project, and Brightway-workspace settings;
- `hex_core.py` calls HEX Core for input and output model schema availability and validation;
- `model_validation.py` rejects failed or incomplete model validation reports;
- `assessment_inputs.py` resolves the requested reference flow and producing activity.
- `foreground.py` assembles selected CE-RISE activities and flows into an internal foreground
  graph, retaining external and elementary exchanges for later linking.
- `foreground_calculation.py` links exact background and biosphere identifiers, builds an
  in-memory foreground datapackage, and runs an internal LCIA.
- `integrated_lca_result.py` builds one environmental indicator and its input references in
  the Integrated LCA result structure.

The HTTP application does not expose Brightway database management. The image build imports
the bundled BONSAI 3.8-beta2 IO release into a seed project containing biosphere flows and
registered impact methods.

## Background Data and Brightway State

The bundled project is `cerise_bonsai`, located by default at
`data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9`. The compressed
seed archive and public IO release are tracked in Git. The expanded local project is ignored;
the image prepares it at build time.

Brightway project state is mutable and process-global. The compatibility probe uses
`BRIGHTWAY_WORKSPACE_DIR` for this writable state and keeps the background project
immutable. Do not use the background source directory as the Brightway workspace.

## API Boundary

`GET /capabilities` is the operational endpoint for checking the background project;
`GET /methods` lists every registered impact-method identifier.
`POST /compute` exposes a JSON schema with model-version fields for `product-system`,
`lci-dataset`, and `integrated-lca`, and requires a functional unit and impact method. It
verifies that HEX Core has JSON Schemas for the requested versions, validates the Product
System and each LCI Dataset, assembles the foreground, and runs an in-memory calculation.
On success it builds an Integrated LCA object, records the configured background project,
service version, and actual `bw2data` and `bw2calc` versions, validates the object through
HEX Core, and returns it.
Model or reference failures return `422`; missing schemas or unavailable HEX Core return
`503`; invalid generated output returns `500` without publishing the object. Singular
calculations return a structured diagnostic rather than a score.

The semantic content of the input objects is the basis for building the internal Brightway
calculation. Foreground assembly resolves selected activities, product outputs, internal inputs,
and the reference output using model identifiers. It does not guess a provider from a matching
unit alone. External background demands and elementary flows remain explicit in the assembled
graph; materialization into a caller-owned writable Brightway database is available only when
those boundaries are absent. The prepared BONSAI project is not modified by foreground
construction. Brightway state is internal to the service; no additional mapping model, API
resource, or persisted record is part of the service boundary.

For calculation, the foreground runner adds a transient Brightway datapackage to the read-only
background and method datapackages. External activity and biosphere flow references must resolve
to exact identifiers in their configured databases; compatible units are converted. The runner
rejects missing links and incompatible units and diagnoses singular calculations. Whether a
particular foreground request is calculable depends on its exact links and demand; the prepared
background is not altered by requests.
