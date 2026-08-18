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

Browser clients normally reach this service through the same-origin gateway.
If a browser must call the service directly from another origin, set
`ALLOWED_ORIGINS` to a comma-separated list of exact trusted origins, such as
`http://localhost:5173`. The default is empty and does not grant cross-origin
access. Wildcards and malformed origins are rejected during application import.

## Tests

```bash
pytest tests/ -v
```

CI validation completed as part of the personal DevSecOps lab.

## PR Diff Review Runner

The provider-independent pipeline and trusted post-CI GitHub Actions integration are documented in [`review_runner/README.md`](review_runner/README.md). Local use accepts a supplied unified patch and uses the mock provider; the trusted reusable workflow retrieves Pull Request diffs as data and invokes OpenRouter only after deterministic CI succeeds.
