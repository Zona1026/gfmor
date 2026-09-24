from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from db.models import PointTransactionType


class PointSummary(BaseModel):
    current_points: int = 0
    balance_points: int = 0
    expiring_soon_points: int = 0
    expiring_soon_days: int = 60


class PointHistoryItem(BaseModel):
    id: str
    name: str
    quantity: int = 1


class PointHistoryRecord(BaseModel):
    id: int
    type: PointTransactionType
    points: int
    source_type: str
    source_id: Optional[int] = None
    source_label: str
    items: List[PointHistoryItem] = Field(default_factory=list)
    issued_at: datetime
    expires_at: Optional[datetime] = None
    note: Optional[str] = None
