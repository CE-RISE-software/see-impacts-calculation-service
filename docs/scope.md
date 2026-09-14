# Project Scope

## Purpose

The service provides the CE-RISE calculation boundary for assessing and reporting the
socio-economic and environmental impacts of products. It is an implementation component in a
digital passport workflow, not a standalone data-model repository or a general-purpose LCA
application.

## Current Constraints

The following constraints define the current scaffold:

- the primary deliverable is a containerized Python HTTP service;
- approved Brightway background data is externally provisioned and excluded from Git and image
  builds;
- background source data is read-only, while Brightway registry state uses a separate writable
  workspace;
- `POST /compute` has a CE-RISE-oriented public request shape but no calculation implementation;
- `hex-core-service` remains the owner of model validation, registry access, and persistence;
- the API and operating guidance are published through the repository's Codeberg Pages site.

## Planned Implementation Boundary

The first calculation implementation is constrained by a versioned mapping and an acceptance
fixture. It will:

- accept selected Product System and LCI Dataset inputs;
- validate inputs through HEX Core;
- create a temporary Brightway foreground calculation against an approved background project;
- perform the defined inventory and impact calculations;
- construct and validate an Integrated LCA result with method, background, mapping, and model
  provenance;
- remove temporary foreground data after each completed calculation.

The mapping and fixture define what may be calculated. They must be introduced before the
service expands its request or response semantics.

## Deliberate Non-Goals For Now

- a generic multi-model calculation platform;
- a public Brightway database-management API;
- embedding or redistributing third-party background datasets in the source repository or image;
- reimplementing CE-RISE model validation outside HEX Core;
- claiming a computed impact result before the mapping and acceptance fixture exist;
- a CLI-first or notebook-first user interface.
