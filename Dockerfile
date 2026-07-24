# ---- Build stage --------------------------------------------------------
FROM python:3.11.9-alpine AS build

WORKDIR /app

# Build tooling for any dependency without a prebuilt musllinux wheel;
# discarded along with this stage, so it never reaches the runtime image.
RUN apk add --no-cache --virtual .build-deps build-base libffi-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Runtime stage --------------------------------------------------------
FROM python:3.11.9-alpine

RUN addgroup -S -g 10001 cart \
    && adduser -S -D -H -u 10001 -G cart cart

WORKDIR /app

COPY --from=build /install /usr/local
COPY --chown=cart:cart . .

USER 10001

EXPOSE 8003

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
