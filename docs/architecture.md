# Architecture

The service separates HTTP handling and model validation from numerical execution. Each
calculation runs in its own worker process and temporary Brightway project. The bundled
background and characterization factors are shared configuration, while the foreground comes
from the request's CE-RISE records.

## Request Execution

1. The HTTP application validates the Product System and LCI Dataset records through HEX Core.
2. Foreground assembly resolves the selected activities, product outputs, internal inputs,
   elementary exchanges, and reference flow.
3. An isolated worker copies the prepared background and adds the foreground as an in-memory
   Brightway datapackage.
4. Brightway solves the inventory once and characterizes it with all configured methods.
5. The application builds one Integrated LCA object, validates it through HEX Core, and returns
   it to the caller.

All indicators must complete successfully. A method failure returns an error rather than a
partial result. Singular calculations return the structured diagnostic described in the
[API Reference](api-reference.md#post-computediagnostics).

## Project Isolation

The bundled project is `cerise_bonsai`, located by default at
`data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9`. The compressed
project archive and its provenance manifest are included in the repository. Source deployments
extract the archive during setup; container builds extract it into the image.

Brightway project state is mutable and process-global. Each compute request therefore runs
in a separate process with a project copy under `BRIGHTWAY_WORKSPACE_DIR/requests`. The copy
is removed when the request completes, fails, or times out. The source background remains
unchanged, and the writable workspace must be outside its directory.

`MAX_CONCURRENT_CALCULATIONS` limits active workers per server process.
`CALCULATION_TIMEOUT_SECS` limits each worker's execution time. Runtime settings and their
defaults are listed under [Deployment](deployment.md#runtime-configuration).

## Foreground Construction

Foreground assembly resolves selected activities, product outputs, internal inputs, and the
reference output using model identifiers. External background demands and elementary flows
retain their identifiers for resolution against the configured databases. Units determine
quantity conversion. Brightway projects and temporary foreground data are managed internally.

For calculation, the foreground runner adds a transient Brightway datapackage to the read-only
background and method datapackages. External activity and biosphere flow references must resolve
to exact identifiers in their configured databases; compatible units are converted. The runner
rejects missing links and incompatible units and diagnoses singular calculations.

## Numerical Calculation

Numerical execution uses SciPy's sparse direct solver with minimum-degree column ordering
(`MMD_AT_PLUS_A`) to reduce factorization fill-in in the shared input-output matrix. The
ordering controls matrix factorization without changing the inventory equations or factors.

After solving the inventory, Brightway switches the characterization method and calculates
each indicator over that same inventory. The service collects the scores, units, method
versions, and factor-set references in one result. Foreground construction and the technosphere
solve are not repeated for different indicators.

## Modules

| Module | Responsibility |
| --- | --- |
| `app.py` | HTTP endpoints, calculation capacity, and validation of the generated result. |
| `config.py` | Service settings and background and workspace locations. |
| `hex_core.py` | Schema retrieval and validation requests to HEX Core. |
| `model_validation.py` | Input and output validation reports and errors. |
| `assessment_inputs.py` | Reference-flow and dataset-reference checks. |
| `foreground.py` | Foreground activities, outputs, exchanges, and links. |
| `foreground_calculation.py` | Background resolution, inventory solving, and characterization. |
| `project_lifecycle.py` | Worker processes, project copies, timeouts, and cleanup. |
| `integrated_lca_result.py` | Integrated LCA output with all indicators and provenance. |
| `prepare_background.py` | Archive verification and extraction. |
| `compatibility.py` | Background, database, and method inspection. |
