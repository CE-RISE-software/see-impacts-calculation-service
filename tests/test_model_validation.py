import asyncio

import pytest

from see_impacts_calculation_service.model_validation import (
    ModelValidationError,
    validate_assessment_inputs,
)


class StubHexCore:
    def __init__(self, report):
        self.report = report
        self.schemas = []
        self.validations = []

    async def schema_available(self, **kwargs):
        self.schemas.append(kwargs)
        return True

    async def validate(self, **kwargs):
        self.validations.append(kwargs)
        return self.report


def validate(client):
    return asyncio.run(
        validate_assessment_inputs(
            client,
            product_system_version="0.0.1",
            lci_dataset_version="0.0.1",
            product_system={"product_system_identifier": "system-1"},
            lci_datasets=[
                {"lci_dataset_identifier": "dataset-1"},
                {"lci_dataset_identifier": "dataset-2"},
            ],
            bearer_token="service-token",
        )
    )


def test_validates_product_system_and_every_lci_dataset():
    client = StubHexCore(
        {"passed": True, "results": [{"kind": "JsonSchema", "passed": True}]}
    )

    validate(client)

    assert [call["model_family"] for call in client.validations] == [
        "product-system",
        "lci-dataset",
        "lci-dataset",
    ]
    assert client.validations[1]["payload"]["lci_dataset_identifier"] == "dataset-1"
    assert client.validations[2]["payload"]["lci_dataset_identifier"] == "dataset-2"
    assert len(client.schemas) == 3
    assert all(call["bearer_token"] == "service-token" for call in client.schemas)


@pytest.mark.parametrize(
    "report",
    [
        {"passed": True, "results": []},
        {"passed": True, "results": [{"kind": "Owl", "passed": True}]},
        {"passed": True, "results": [{"kind": "JsonSchema", "passed": False}]},
    ],
)
def test_rejects_reports_without_a_successful_json_schema_check(report):
    with pytest.raises(ModelValidationError) as error:
        validate(StubHexCore(report))

    assert error.value.status_code == 502
    assert error.value.code == "MODEL_VALIDATION_RESPONSE_INVALID"
