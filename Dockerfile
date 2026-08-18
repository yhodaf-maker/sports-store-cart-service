# ---- Build stage --------------------------------------------------------
FROM python:3.11.15-slim-trixie@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93 AS build

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Runtime stage ------------------------------------------------------
FROM python:3.11.15-slim-trixie@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93

RUN apt-get update \
    && apt-get install --yes --no-install-recommends --only-upgrade \
      bsdutils libblkid1 liblastlog2-2 libmount1 libsmartcols1 libuuid1 \
      login mount util-linux \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall --yes pip setuptools wheel \
    && groupadd --gid 10001 cart \
    && useradd --uid 10001 --gid cart --no-create-home --home-dir /app \
      --shell /usr/sbin/nologin cart

WORKDIR /app

COPY --from=build /install /usr/local
COPY --chown=cart:cart . .

USER 10001:10001

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8003/health', timeout=4).read()"]

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
