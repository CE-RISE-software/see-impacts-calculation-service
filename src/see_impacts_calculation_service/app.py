"""HTTP service for CE-RISE SEE impacts background-project inspection."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from . import __version__
from .compatibility import BrightwayCompatibilityError, run_probe
from .config import RuntimeConfig


class ModelVersions(BaseModel):
    product_system: str = Field(description="Version of the input product-system model.")
    lci_dataset: str = Field(description="Version of the input lci-dataset model.")
    integrated_lca: str = Field(description="Version of the output integrated-lca model.")


class ComputeRequest(BaseModel):
    """CE-RISE input objects used to build an internal Brightway calculation."""

    model_versions: ModelVersions
    product_system: dict[str, Any] = Field(
        description="Input object conforming to the selected product-system version."
    )
    lci_datasets: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Input objects conforming to the selected lci-dataset version.",
    )
    assessment_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional information supplied with the assessment inputs.",
    )


def create_app(config: RuntimeConfig | None = None) -> FastAPI:
    runtime_config = config or RuntimeConfig.from_env()
    app = FastAPI(
        title="CE-RISE SEE Impacts Calculation Service",
        version=__version__,
        description=(
            "Inspect the configured Brightway background project. "
            "Impact calculation is not available."
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
            "calculation_status": "not_available",
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

    @app.post(
        "/compute",
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        response_description="Impact calculation is not available.",
    )
    async def compute(request: ComputeRequest) -> dict[str, Any]:
        del request
        raise HTTPException(
            status_code=501,
            detail={
                "code": "CALCULATION_NOT_IMPLEMENTED",
                "message": (
                    "Impact calculation is not available. Use GET /capabilities to verify "
                    "the configured Brightway project."
                ),
            },
        )

    return app


app = create_app()
