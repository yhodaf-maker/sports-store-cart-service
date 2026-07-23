# Sports Store Cart Service

FastAPI service responsible for per-user carts, product snapshots, quantity updates, and subtotal calculation.

## Runtime

- Port: `8003`
- Database: `cart_db`
- Dependency: Catalog service
- Health endpoint: `/health`

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8003
```

## Tests

```bash
pytest tests/ -v
```
