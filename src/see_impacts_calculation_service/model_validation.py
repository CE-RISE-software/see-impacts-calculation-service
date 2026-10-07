"""Validate CE-RISE assessment inputs through HEX Core."""

from __future__ import annotations

from typing import Any

import httpx

from .hex_core import HexCoreClient


class ModelValidationError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        field: str,
        message: str,
        results: list[Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.field = field
        self.results = results
        super().__init__(message)

    def detail(self) -> dict[str, Any]:
        detail: dict[str, Any] = {
            "code": self.code,
            "field": self.field,
            "message": str(self),
        }
        if self.results is not None:
            detail["results"] = self.results
        return detail


async def validate_assessment_inputs(
    client: HexCoreClient,
    *,
    product_system_version: str,
    lci_dataset_version: str,
    product_system: dict[str, Any],
    lci_datasets: list[dict[str, Any]],
    bearer_token: str | None = None,
) -> None:
    records = [
        ("product-system", product_system_version, product_system, "product_system"),
        *(
            ("lci-dataset", lci_dataset_version, dataset, f"lci_datasets[{index}]")
            for index, dataset in enumerate(lci_datasets)
        ),
    ]
    for model_family, model_version, payload, field in records:
        await validate_model_payload(
            client,
            model_family=model_family,
            model_version=model_version,
            payload=payload,
            field=field,
            bearer_token=bearer_token,
        )


async def validate_model_payload(
    client: HexCoreClient,
    *,
    model_family: str,
    model_version: str,
    payload: dict[str, Any],
    field: str,
    bearer_token: str | None = None,
    output: bool = False,
) -> None:
    """Require an available schema and a complete, passing HEX Core validation report."""

    try:
        schema_available = await client.schema_available(
            model_family=model_family,
            model_version=model_version,
            bearer_token=bearer_token,
        )
    except httpx.HTTPError as error:
        raise ModelValidationError(
            status_code=503,
            code="MODEL_VALIDATION_UNAVAILABLE",
            field=field,
            message=f"HEX Core could not resolve {model_family} version {model_version}.",
        ) from error
    if not schema_available:
        raise ModelValidationError(
            status_code=503,
            code="MODEL_SCHEMA_UNAVAILABLE",
            field=field,
            message=f"HEX Core has no JSON Schema for {model_family} version {model_version}.",
        )

    try:
        report = await client.validate(
            model_family=model_family,
            model_version=model_version,
            payload=payload,
            bearer_token=bearer_token,
        )
    except (httpx.HTTPError, ValueError) as error:
        raise ModelValidationError(
            status_code=503,
            code="MODEL_VALIDATION_UNAVAILABLE",
            field=field,
            message=f"HEX Core could not validate {model_family} version {model_version}.",
        ) from error

    if (
        not isinstance(report, dict)
        or type(report.get("passed")) is not bool
        or not isinstance(report.get("results"), list)
        or not any(
            isinstance(result, dict)
            and result.get("kind") == "JsonSchema"
            and type(result.get("passed")) is bool
            for result in report["results"]
        )
        or (
            report["passed"]
            and not all(
                isinstance(result, dict) and result.get("passed") is True
                for result in report["results"]
            )
        )
    ):
        raise ModelValidationError(
            status_code=502,
            code="MODEL_VALIDATION_RESPONSE_INVALID",
            field=field,
            message=f"HEX Core returned an invalid validation report for {model_family}.",
        )
    if not report["passed"]:
        raise ModelValidationError(
            status_code=500 if output else 422,
            code="OUTPUT_MODEL_VALIDATION_FAILED" if output else "MODEL_VALIDATION_FAILED",
            field=field,
            message=f"{model_family} does not conform to version {model_version}.",
            results=report["results"],
        )
