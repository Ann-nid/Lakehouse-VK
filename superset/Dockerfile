FROM apache/superset:4.1.2
USER root
# драйвер Trino для Superset
RUN (pip install --no-cache-dir "trino[sqlalchemy]") || (uv pip install --python /app/.venv/bin/python "trino[sqlalchemy]")
USER superset
