FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts
COPY README.md ARCHITECTURE_TRACEABILITY.md ./
RUN mkdir -p /app/uploads
COPY docker-entrypoint.sh ./
RUN chmod +x /app/docker-entrypoint.sh
CMD ["/app/docker-entrypoint.sh"]
