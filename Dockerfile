FROM python:3.12-slim
WORKDIR /app
COPY src ./src
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
ENV PYTHONPATH=/app/src
CMD ["uvicorn", "apc.api:app", "--host", "0.0.0.0", "--port", "8080"]
