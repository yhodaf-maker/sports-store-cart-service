import logging

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from cors_config import add_cors_middleware
from database import carts_collection
from routes import cart

logger = logging.getLogger("cart-service")

app = FastAPI(title="Sports Store — Cart Service")

add_cors_middleware(app)

app.include_router(cart.router, prefix="/api")

# Prometheus metrics (DEP-263, Sub-PRD 7 2.1.2). Exposes GET /metrics with
# http_requests_total and http_request_duration_seconds — the series the
# Sub-PRD 6 canary AnalysisTemplate queries. Labels are limited to
# method/handler/status; `handler` is the templated route path, never the raw
# id, so high-cardinality values (user_id/order_id/cart_id) are never emitted
# as label values (AC 2.1.2.2).
Instrumentator(excluded_handlers=["/metrics", "/health"]).add(
    metrics.requests(metric_name="http_requests_total")
).add(
    metrics.latency(metric_name="http_request_duration_seconds")
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.on_event("startup")
async def create_indexes():
    try:
        await carts_collection.create_index("user_id", unique=True)
    except PyMongoError as exc:  # Mongo may be unavailable (e.g. unit tests)
        logger.warning("Index creation skipped: %s", exc)

    # Verify Redis connectivity
    try:
        from cache import redis_client
        redis_client.ping()
        logger.info("Redis connection verified.")
    except RedisError as exc:
        logger.warning("Redis is offline: %s", exc)


@app.get("/health")
def health():
    return {"status": "ok", "service": "cart-service"}
