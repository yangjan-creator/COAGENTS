FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock ./
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.lock
COPY src ./src
COPY README.md LICENSE ./
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-deps .
ENV PYTHONPATH=/app/src
CMD ["uvicorn", "apc.api:app", "--host", "0.0.0.0", "--port", "8080"]
