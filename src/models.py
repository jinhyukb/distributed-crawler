from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class BookData(BaseModel):
    title: str = Field(..., min_length=1)
    price: float = Field(..., gt=0.0)
    in_stock: bool = Field(default=True)
    rating: int = Field(..., ge=1, le=5)
    detail_url: str = Field(...)
    image_url: str = Field(..., description="도서 썸네일 이미지 URL")
    author: str = Field(..., description="도서 저자")
    description: str = Field(..., description="도서 세부 설명")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("price", mode="before")
    @classmethod
    def clean_price(cls, v):
        if isinstance(v, str):
            cleaned = "".join(c for c in v if c.isdigit() or c == '.')
            return float(cleaned)
        return v
