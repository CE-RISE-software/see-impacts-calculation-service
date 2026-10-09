FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BRIGHTWAY_WORKSPACE_DIR=/var/lib/see-impacts/brightway

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /var/lib/see-impacts/brightway \
    && chown -R appuser:appuser /var/lib/see-impacts

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY data/background/cerise_bonsai.tar.gz ./data/background/

RUN mkdir -p data/background/projects \
    && tar -xzf data/background/cerise_bonsai.tar.gz -C data/background/projects \
    && chmod -R a-w data/background/projects \
    && rm data/background/cerise_bonsai.tar.gz \
    && pip install --no-cache-dir .

EXPOSE 8080

USER appuser

CMD ["python", "-m", "uvicorn", "see_impacts_calculation_service.app:app", "--host", "0.0.0.0", "--port", "8080"]
