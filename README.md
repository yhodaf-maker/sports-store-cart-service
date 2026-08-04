# Sports Store Cart Service

Shopping-cart service for the Sports Store platform. It keeps a separate cart for each authenticated user, snapshots product details, changes quantities, and calculates subtotals.

## Role and request flow

The [gateway](https://github.com/Deploy-On-Friday2-0/sports-store-gateway) sends `/api/cart` requests here on port `8003`. The service verifies the user's JWT, reads product data from the catalog service, stores carts in the `cart_db` MongoDB database, and can cache data in Redis. The order service reads and clears carts during checkout.

## Technology and structure

- Python, FastAPI, HTTPX, Motor, PyJWT, Redis, Pydantic, and Prometheus instrumentation.
- `routes/cart.py` implements cart operations; `catalog_client.py` calls the catalog.
- `models.py`, `database.py`, `security.py`, and `cache.py` contain core support logic.
- `tests/`, `.github/workflows/`, and `review_runner/` contain tests, automation, and the [optional reviewer](review_runner/README.md).

## Configuration

| Variable | Purpose | Default/example |
| --- | --- | --- |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `JWT_SECRET` | Verifies user tokens | local placeholder in `.env.example` |
| `CATALOG_URL` | Catalog base URL | `http://localhost:8002` |
| `REDIS_HOST`, `REDIS_PORT` | Standalone cache | `localhost`, `6379` |
| `REDIS_SENTINELS`, `REDIS_MASTER_NAME` | Optional Sentinel cache | unset, `mymaster` |
| `REDIS_PASSWORD`, `REDIS_SOCKET_TIMEOUT` | Optional Redis settings | unset, `0.2` seconds |

`OPENROUTER_*` configures only the review runner. Keep real secrets out of `.env` commits.

## Local development

Prerequisites: Python 3, MongoDB, the catalog service, and optionally Redis. For the complete dependency graph, use [sports-store-local](https://github.com/Deploy-On-Friday2-0/sports-store-local).

```bash
python -m venv .venv
source .venv/bin/activate       # PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
cp .env.example .env
uvicorn main:app --reload --port 8003
```

Interactive API documentation is at `http://localhost:8003/docs`.

## API summary

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/cart` | Read the user's cart |
| `POST` | `/api/cart/items` | Add an item |
| `PUT` | `/api/cart/items/{sku}` | Change quantity |
| `DELETE` | `/api/cart/items/{sku}` | Remove an item |
| `DELETE` | `/api/cart` | Empty the cart |
| `GET` | `/health`, `/metrics` | Health and metrics |

## Validate, package, and deploy

```bash
ruff check .
python -m pytest
python -m pip check
docker build -t sports-store-cart-service:local .
docker run --rm -p 8003:8003 --env-file .env sports-store-cart-service:local
```

`PR Quality and Security` runs quality, test, secret, Dockerfile, and image scans. `Publish Production Image` publishes to Amazon ECR and changes the image value in [sports-store-deployments](https://github.com/Deploy-On-Friday2-0/sports-store-deployments); Argo CD performs deployment.

## Troubleshooting and security

- A catalogue connection error usually means `CATALOG_URL` is wrong or port `8002` is unavailable.
- For health failures, inspect MongoDB and Redis connectivity. A `401` usually indicates an absent, expired, or differently signed JWT.
- Use one strong `JWT_SECRET` across backends and a secret manager in production. Follow [CONTRIBUTING.md](CONTRIBUTING.md) for changes.
