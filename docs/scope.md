# Project Scope

## Available Scope

The repository provides a containerized Python HTTP service for inspecting an approved Brightway
background project. The usable operations are the command-line compatibility probe, health
endpoint, capability endpoint, OpenAPI document, and container release workflow.

Background source data remains local and read-only. Brightway registry state uses a separate
writable workspace. The API and operating guidance are published through the repository's
Codeberg Pages site.

## Not Provided

- impact calculation through `POST /compute`;
- Product System, LCI Dataset, or Integrated LCA payload validation;
- HEX Core calls from the HTTP service;
- a Brightway database-management API;
- background datasets embedded in the source repository or container image;
- a general-purpose LCA application, CLI, or notebook interface.
