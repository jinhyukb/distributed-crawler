from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator

class BookData(BaseModel):
    title: str = Field(..., min_length=1)
    price: float = Field(..., gt=0.0)
    in_stock: bool = Field(default=True)
    rating: int = Field(..., ge=1, le=5)
    detail_url: HttpUrl = Field(...)
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("price", mode="before")
    @classmethod
    def clean_price(cls, v):
        if isinstance(v, str):
            cleaned = "".join(c for c in v if c.isdigit() or c == '.')
            return float(cleaned)
        return v
