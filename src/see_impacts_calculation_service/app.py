"""HTTP service for CE-RISE SEE impacts calculation diagnostics."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from . import __version__
from .assessment_inputs import AssessmentInputError
from .compatibility import BrightwayCompatibilityError, list_methods, run_probe
from .config import RuntimeConfig
from .foreground import ForegroundConstructionError, assemble_foreground
from .foreground_calculation import ForegroundCalculationError, ForegroundImpact
from .hex_core import HexCoreClient
from .integrated_lca_result import build_integrated_lca_result
from .model_validation import ModelValidationError, validate_assessment_inputs, validate_model_payload
from .project_lifecycle import IsolatedWorkerError, calculate_isolated_foreground as calculate_foreground


class ModelVersions(BaseModel):
    product_system: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]*$",
        description="Version of the input product-system model.",
    )
    lci_dataset: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]*$",
        description="Version of the input lci-dataset model.",
    )
    integrated_lca: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]*$",
        description="Version of the output integrated-lca model.",
    )


class FunctionalUnit(BaseModel):
    reference_flow_identifier: str = Field(min_length=1)
    quantity: float = Field(gt=0, allow_inf_nan=False)
    unit: str = Field(min_length=1)


class ComputeRequest(BaseModel):
    """CE-RISE input objects used to build an internal Brightway calculation."""

    model_config = ConfigDict(extra="forbid")

    model_versions: ModelVersions
    product_system: dict[str, Any] = Field(
        description="Input object conforming to the selected product-system version."
    )
    lci_datasets: list[dict[str, Any]] = Field(
        min_length=1,
        description="Input objects conforming to the selected lci-dataset version.",
    )
    functional_unit: FunctionalUnit = Field(
        description="Requested quantity and unit for the Product System reference flow."
    )
    impact_method: list[str] = Field(
        min_length=1,
        description="Registered Brightway impact-method identifier for this request.",
    )


def create_app(
    config: RuntimeConfig | None = None, hex_core_client: HexCoreClient | None = None
) -> FastAPI:
    runtime_config = config or RuntimeConfig.from_env()
    validator = hex_core_client or HexCoreClient(
        runtime_config.hex_core_base_url, runtime_config.http_timeout_secs
    )
    app = FastAPI(
        title="CE-RISE SEE Impacts Calculation Service",
        version=__version__,
        description=(
            "Calculate CE-RISE environmental impacts and return HEX Core-validated "
            "Integrated LCA results or request-specific diagnostics."
        ),
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "see-impacts-calculation-service",
            "version": __version__,
            "hex_core_base_url": runtime_config.hex_core_base_url,
            "background_project_dir": str(runtime_config.background_project_dir),
        }

    @app.get("/capabilities")
    async def capabilities() -> dict[str, Any]:
        try:
            report = run_probe(
                runtime_config.background_project_dir,
                runtime_config.brightway_workspace_dir,
                runtime_config.background_project_name,
            )
        except BrightwayCompatibilityError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "BRIGHTWAY_PROJECT_UNAVAILABLE", "message": str(error)},
            ) from error

        return {
            "calculation_status": "request_dependent",
            "background": {
                "project_name": report.declared_project_name,
                "databases": [database.__dict__ for database in report.databases],
                "method_count": report.method_count,
                "method_examples": report.method_examples,
            },
            "brightway": {
                "bw2data_version": report.bw2data_version,
                "bw2calc_version": report.bw2calc_version,
            },
        }

    @app.get("/methods")
    async def methods() -> dict[str, Any]:
        try:
            project_name, identifiers = list_methods(
                runtime_config.background_project_dir,
                runtime_config.brightway_workspace_dir,
                runtime_config.background_project_name,
            )
        except BrightwayCompatibilityError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "BRIGHTWAY_PROJECT_UNAVAILABLE", "message": str(error)},
            ) from error
        return {
            "project_name": project_name,
            "method_count": len(identifiers),
            "methods": identifiers,
        }

    async def _calculate(request: ComputeRequest) -> tuple[ForegroundImpact | None, dict[str, Any], dict[str, Any] | None]:
        try:
            await validate_assessment_inputs(
                validator,
                product_system_version=request.model_versions.product_system,
                lci_dataset_version=request.model_versions.lci_dataset,
                product_system=request.product_system,
                lci_datasets=request.lci_datasets,
                bearer_token=runtime_config.hex_core_bearer_token,
            )
        except ModelValidationError as error:
            raise HTTPException(status_code=error.status_code, detail=error.detail()) from error

        try:
            assembly = assemble_foreground(
                request.product_system,
                request.lci_datasets,
                reference_flow_identifier=request.functional_unit.reference_flow_identifier,
                quantity=request.functional_unit.quantity,
                unit=request.functional_unit.unit,
            )
        except AssessmentInputError as error:
            raise HTTPException(
                status_code=422,
                detail={"code": "CALCULATION_INPUT_INVALID", "field": error.field, "message": str(error)},
            ) from error
        except ForegroundConstructionError as error:
            raise HTTPException(
                status_code=422,
                detail={"code": "FOREGROUND_CONSTRUCTION_FAILED", "message": str(error)},
            ) from error

        request_summary = {
            "product_system_identifier": assembly.demand.product_system_identifier,
            "functional_unit": request.functional_unit.model_dump(),
            "impact_method": request.impact_method,
        }
        try:
            impact = await calculate_foreground(
                assembly,
                project_dir=runtime_config.background_project_dir,
                workspace_dir=runtime_config.brightway_workspace_dir,
                project_name=runtime_config.background_project_name,
                background_database_name=runtime_config.background_database_name,
                biosphere_database_name=runtime_config.biosphere_database_name,
                method=tuple(request.impact_method),
                timeout_secs=runtime_config.calculation_timeout_secs,
            )
        except IsolatedWorkerError as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "CALCULATION_WORKER_UNAVAILABLE", "message": str(error)},
            ) from error
        except ForegroundCalculationError as error:
            if error.diagnostic is not None:
                return None, request_summary, {
                    "status": "not_calculable",
                    "request": request_summary,
                    "diagnostic": asdict(error.diagnostic),
                }
            raise HTTPException(
                status_code=422,
                detail={"code": "CALCULATION_PRECONDITION_FAILED", "message": str(error)},
            ) from error
        return impact, request_summary, None

    @app.post("/compute")
    async def compute(request: ComputeRequest) -> dict[str, Any]:
        impact, _, diagnostic = await _calculate(request)
        if diagnostic is not None:
            return diagnostic
        assert impact is not None
        result = build_integrated_lca_result(
            impact,
            product_system_version=request.model_versions.product_system,
            lci_dataset_version=request.model_versions.lci_dataset,
            product_system=request.product_system,
            lci_datasets=request.lci_datasets,
            background_project_name=runtime_config.background_project_name,
            background_database_name=runtime_config.background_database_name,
            software_version=__version__,
        )
        try:
            await validate_model_payload(
                validator,
                model_family="integrated-lca",
                model_version=request.model_versions.integrated_lca,
                payload=result,
                field="integrated_lca",
                bearer_token=runtime_config.hex_core_bearer_token,
                output=True,
            )
        except ModelValidationError as error:
            raise HTTPException(status_code=error.status_code, detail=error.detail()) from error
        return result

    @app.post("/compute/diagnostics")
    async def compute_diagnostics(request: ComputeRequest) -> dict[str, Any]:
        _, request_summary, diagnostic = await _calculate(request)
        return diagnostic or {"status": "calculable", "request": request_summary, "diagnostic": None}

    return app


app = create_app()
