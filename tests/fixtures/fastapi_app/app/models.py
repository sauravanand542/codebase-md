"""Pydantic models."""

from pydantic import BaseModel


class Item(BaseModel):
    """An item in the store."""

    name: str
    price: float
    in_stock: bool = True
