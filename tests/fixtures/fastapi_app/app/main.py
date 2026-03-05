"""FastAPI application entry point."""

from fastapi import FastAPI
from app.models import Item

app = FastAPI(title="My API")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Hello, World!"}


@app.post("/items")
async def create_item(item: Item) -> Item:
    """Create a new item."""
    return item
