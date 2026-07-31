FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e .

EXPOSE 8100

CMD ["uvicorn", "assurance_coordinator.main:app", "--host", "0.0.0.0", "--port", "8100"]
