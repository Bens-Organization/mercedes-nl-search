"""Pydantic models for type validation."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PriceInfo(BaseModel):
    """Price information."""
    value: float
    currency: str = "USD"


class ProductImage(BaseModel):
    """Product image."""
    url: str
    label: Optional[str] = None


class ProductCategory(BaseModel):
    """Product category."""
    id: int
    name: str
    url_path: Optional[str] = None


class Product(BaseModel):
    """Product model for search results."""
    product_id: str  # Changed to str to support SKU as ID
    sku: str
    name: str
    url_key: str
    stock_status: str
    product_type: str = "simple"  # Renamed from type_id for consistency
    description: Optional[str] = None
    short_description: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    image_url: Optional[str] = None
    categories: List[str] = Field(default_factory=list)


class SearchQuery(BaseModel):
    """Search query from user."""
    query: str
    max_results: int = Field(default=20, ge=1, le=100)


class TypesenseQuery(BaseModel):
    """Structured Typesense query parameters."""
    q: str = "*"  # Search query
    filter_by: Optional[str] = None  # Filters like "price:[100..500]"
    sort_by: Optional[str] = None  # Sort criteria
    per_page: int = 20


class SearchResponse(BaseModel):
    """Search response with confidence scoring."""
    results: List[Product]  # All results (for backwards compatibility)
    primary_results: Optional[List[Product]] = None  # Results matching detected category
    additional_results: Optional[List[Product]] = None  # Results from other categories
    detected_category: Optional[str] = None  # The category that was detected
    category_confidence: Optional[float] = None  # Confidence score (0-1) for category detection
    category_applied: Optional[bool] = None  # Whether category filter was applied
    confidence_threshold: Optional[float] = None  # Minimum confidence threshold used
    total: int
    query_time_ms: float
    typesense_query: Dict[str, Any]
