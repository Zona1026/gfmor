from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class PromotionInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field('', max_length=5000)
    starts_at: datetime
    ends_at: datetime
    discount_type: Literal['PERCENT', 'AMOUNT', 'BOGO']
    discount_value: int = Field(1, gt=0, le=1000000)
    is_active: bool = True
    product_ids: list[int] = Field(min_length=1, max_length=1000)
    buy_quantity: int = Field(1, gt=0, le=1000000)
    gift_quantity: int = Field(1, gt=0, le=1000000)
    gift_product_id: int | None = Field(None, gt=0)
    allow_discount_stacking: bool = False

    @field_validator('name', mode='before')
    @classmethod
    def clean_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('starts_at', 'ends_at')
    @classmethod
    def utc_time(cls, value):
        if value.tzinfo is None:
            raise ValueError('活動時間必須包含時區')
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    @model_validator(mode='after')
    def validate_settings(self):
        if self.ends_at <= self.starts_at:
            raise ValueError('結束時間必須晚於開始時間')
        if self.discount_type == 'PERCENT' and self.discount_value > 100:
            raise ValueError('折扣百分比不可超過 100')
        if self.discount_type == 'BOGO' and self.gift_product_id is None:
            raise ValueError('買A送B必須設定贈品')
        if self.discount_type != 'BOGO':
            self.gift_product_id = None
            self.allow_discount_stacking = False
        if any(value <= 0 for value in self.product_ids):
            raise ValueError('商品編號無效')
        self.product_ids = list(dict.fromkeys(self.product_ids))
        return self


class PromotionPreviewLine(BaseModel):
    product_id: int | None = None
    quantity: int = Field(1, gt=0, le=1000000)
    type: str = 'PART'
    promotion_gift_id: int | None = None
    is_confirmed: int = 1


class PromotionPreview(BaseModel):
    line_items: list[PromotionPreviewLine] = Field(default_factory=list, max_length=1000)
