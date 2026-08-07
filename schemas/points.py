from pydantic import BaseModel


class PointSummary(BaseModel):
    current_points: int = 0
    balance_points: int = 0
    expiring_soon_points: int = 0
    expiring_soon_days: int = 60
