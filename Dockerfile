FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BRIGHTWAY_WORKSPACE_DIR=/var/lib/see-impacts/brightway

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /var/lib/see-impacts/brightway \
    && chown -R appuser:appuser /var/lib/see-impacts

COPY pyproject.toml README.md LICENSE requirements-background-build.txt ./
COPY src ./src
COPY data/background/cerise_bonsai.tar.gz ./data/background/
COPY data/background/bonsai-3.8-beta2 ./data/background/bonsai-3.8-beta2

RUN pip install --no-cache-dir . \
    && pip install --no-cache-dir -r requirements-background-build.txt \
    && python -m see_impacts_calculation_service.prepare_background \
        data/background/cerise_bonsai.tar.gz data/background/projects \
        --project-name cerise_bonsai \
    && python -m see_impacts_calculation_service.import_bonsai \
        data/background/bonsai-3.8-beta2 \
        data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9 \
        --project-name cerise_bonsai \
    && python -m see_impacts_calculation_service.compatibility \
        --project-dir data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9 \
        --project-name cerise_bonsai \
        --workspace-dir /tmp/see-impacts-build-probe \
    && chmod -R a-w data/background/projects \
    && rm -rf data/background/cerise_bonsai.tar.gz data/background/bonsai-3.8-beta2 \
        /tmp/see-impacts-build-probe

RUN chmod -R a+rX data/background/projects

EXPOSE 8080

USER appuser

RUN python -c 'from fastapi.testclient import TestClient; from see_impacts_calculation_service.app import app; response = TestClient(app).get("/capabilities"); assert response.status_code == 200, response.text'

CMD ["python", "-m", "uvicorn", "see_impacts_calculation_service.app:app", "--host", "0.0.0.0", "--port", "8080"]
