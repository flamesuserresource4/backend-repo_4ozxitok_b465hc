import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Any
from schemas import Product, Order
from database import db, create_document, get_documents

app = FastAPI(title="E-Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "E-Commerce Backend is running"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


def _serialize(doc: dict) -> dict:
    """Convert Mongo ObjectId to string and return clean dict"""
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Convert any nested ObjectIds if present (not expected here)
    return d


def _ensure_seed_products() -> None:
    """Seed database with sample products if empty"""
    if db is None:
        return
    count = db["product"].count_documents({})
    if count == 0:
        sample_products = [
            {
                "title": "Classic Tee",
                "description": "Soft cotton tee in a relaxed fit.",
                "price": 19.99,
                "category": "Apparel",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=800&q=80&auto=format&fit=crop"
            },
            {
                "title": "Canvas Sneakers",
                "description": "Everyday low-top sneakers with cushioned soles.",
                "price": 49.0,
                "category": "Shoes",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1528701800489-20beeb13d1d1?w=800&q=80&auto=format&fit=crop"
            },
            {
                "title": "Leather Backpack",
                "description": "Durable backpack with laptop sleeve.",
                "price": 89.5,
                "category": "Bags",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1521133573892-e44906baee46?w=800&q=80&auto=format&fit=crop"
            },
            {
                "title": "Aviator Sunglasses",
                "description": "UV400 protection with classic metal frame.",
                "price": 29.95,
                "category": "Accessories",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=800&q=80&auto=format&fit=crop"
            },
        ]
        # Validate with Product schema then insert
        validated = [Product(**p).model_dump() for p in sample_products]
        db["product"].insert_many(validated)


@app.get("/api/products")
def list_products() -> List[dict]:
    if db is None:
        # Return static fallback to keep demo working if DB isn't available
        return [
            {
                "id": "demo-1",
                "title": "Classic Tee",
                "description": "Soft cotton tee in a relaxed fit.",
                "price": 19.99,
                "category": "Apparel",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=800&q=80&auto=format&fit=crop",
            }
        ]

    _ensure_seed_products()
    docs = get_documents("product")
    return [_serialize(d) for d in docs]


@app.post("/api/orders")
def create_order(order: Order) -> dict:
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    # Simple stock check: ensure all items have positive qty
    if not order.items or any(i.quantity <= 0 for i in order.items):
        raise HTTPException(status_code=400, detail="Invalid order items")

    order_id = create_document("order", order)
    return {"order_id": order_id, "status": "received"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
