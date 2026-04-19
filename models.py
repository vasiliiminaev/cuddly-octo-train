"""Pydantic models for request/response shapes."""
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class ScrapeRequest(BaseModel):
    url: HttpUrl = Field(..., description="Property listing URL")


class ScrapeResponse(BaseModel):
    url: str
    source: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "EUR"
    size: Optional[float] = None
    size_unit: Optional[str] = "m2"
    location: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    rooms: Optional[int] = None
    bathrooms: Optional[int] = None
    images: List[str] = []


class ErrorResponse(BaseModel):
    error: str
