# HEX Core Integration

## Model Validation

Both compute endpoints check the Product System and each LCI Dataset against the versions named
in `model_versions`. After a successful calculation, `POST /compute` also validates its
generated Integrated LCA object against `model_versions.integrated_lca`. For each record, the
service first requests the JSON Schema artifact from HEX Core and then calls:

```text
POST /models/{model-family}/versions/{version}:validate
```

The schema check prevents a missing artifact from appearing as a successful validation.
The validation report must include a JSON Schema result. A failed input report returns `422`
with HEX Core's findings. A failed output report returns `500`, and the generated result is not
published. An unavailable schema or HEX Core returns `503`; a malformed report returns `502`.
Only after input validation does the service check reference-flow links.

Set `HEX_CORE_BASE_URL` to the running HEX Core service. If it requires bearer-token
authentication, provide `HEX_CORE_BEARER_TOKEN` through deployment secrets. The token is
sent only to HEX Core and is not included in the health response.

## CE-RISE Data Boundary

The `POST /compute` JSON schema uses the following CE-RISE contracts:

- [Product System](https://codeberg.org/CE-RISE-models/product-system): input object
- [LCI Dataset](https://codeberg.org/CE-RISE-models/lci-dataset): input object(s)
- [Integrated LCA](https://codeberg.org/CE-RISE-models/integrated-lca): result object

Brightway remains inside the calculation service. No additional mapping object or API is
required from callers. The output is returned only after HEX Core validation passes.
