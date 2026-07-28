# ---- Build stage --------------------------------------------------------
FROM python:3.11-slim-bookworm AS build

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --target=/opt/python -r requirements.txt

# ---- Runtime stage --------------------------------------------------------
FROM gcr.io/distroless/python3-debian12:nonroot

WORKDIR /app

ENV PYTHONPATH=/opt/python

COPY --from=build --chown=nonroot:nonroot /opt/python /opt/python
COPY --chown=nonroot:nonroot . .

USER nonroot

EXPOSE 8003

CMD ["-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
