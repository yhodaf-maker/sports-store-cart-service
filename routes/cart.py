from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import catalog_client
from database import carts_collection
from models import AddItemRequest, UpdateItemRequest
from security import bearer_scheme, get_current_user

router = APIRouter(prefix="/cart", tags=["cart"])


def cart_response(items: list[dict]) -> dict:
    subtotal = round(sum(i["quantity"] * i["unit_price"] for i in items), 2)
    return {"items": items, "subtotal": subtotal}


import json
from cache import redis_client

async def load_items(user_id: str) -> list[dict]:
    cache_key = f"cart:{user_id}"
    try:
        # Check cache first
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached.decode("utf-8"))
    except Exception as e:
        # Fail-safe: log warning but don't fail the request (resilient database fallback)
        print(f"WARNING: Redis read error: {e}")

    # Cache miss -> Query MongoDB
    cart = await carts_collection.find_one({"user_id": user_id})
    items = cart["items"] if cart else []

    # Write-through: Populate cache with 24h TTL
    try:
        redis_client.set(cache_key, json.dumps(items), ex=86400)
    except Exception as e:
        print(f"WARNING: Redis write error: {e}")
        
    return items


async def save_items(user_id: str, items: list[dict]) -> None:
    # Save to MongoDB
    await carts_collection.update_one(
        {"user_id": user_id},
        {"$set": {"items": items, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    # Instantly update cache
    try:
        redis_client.set(f"cart:{user_id}", json.dumps(items), ex=86400)
    except Exception as e:
        print(f"WARNING: Redis write error: {e}")


@router.get("")
async def get_cart(user: dict = Depends(get_current_user)):
    return cart_response(await load_items(user["sub"]))


@router.post("/items")
async def add_item(
    payload: AddItemRequest,
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    variant = await catalog_client.get_variant(payload.sku, credentials.credentials)

    items = await load_items(user["sub"])
    existing = next((i for i in items if i["sku"] == payload.sku), None)
    new_quantity = payload.quantity + (existing["quantity"] if existing else 0)
    if variant["stock_quantity"] < new_quantity:
        raise HTTPException(status_code=409, detail="Insufficient stock")

    if existing:
        existing["quantity"] = new_quantity
    else:
        items.append(
            {
                "product_id": variant["product_id"],
                "sku": variant["sku"],
                "name": variant["name"],
                "size": variant["size"],
                "color": variant["color"],
                "quantity": payload.quantity,
                "unit_price": variant["price"],
                "image_url": variant["image_url"],
            }
        )
    await save_items(user["sub"], items)
    return cart_response(items)


@router.put("/items/{sku}")
async def update_item(
    sku: str,
    payload: UpdateItemRequest,
    user: dict = Depends(get_current_user),
):
    items = await load_items(user["sub"])
    existing = next((i for i in items if i["sku"] == sku), None)
    if existing is None:
        raise HTTPException(status_code=404, detail="Item not in cart")
    if payload.quantity == 0:
        items = [i for i in items if i["sku"] != sku]
    else:
        existing["quantity"] = payload.quantity
    await save_items(user["sub"], items)
    return cart_response(items)


@router.delete("/items/{sku}")
async def remove_item(sku: str, user: dict = Depends(get_current_user)):
    items = await load_items(user["sub"])
    if not any(i["sku"] == sku for i in items):
        raise HTTPException(status_code=404, detail="Item not in cart")
    items = [i for i in items if i["sku"] != sku]
    await save_items(user["sub"], items)
    return cart_response(items)


@router.delete("")
async def clear_cart(user: dict = Depends(get_current_user)):
    await carts_collection.delete_one({"user_id": user["sub"]})
    try:
        redis_client.delete(f"cart:{user['sub']}")
    except Exception as e:
        print(f"WARNING: Redis delete error: {e}")
    return {"message": "Cart cleared"}
