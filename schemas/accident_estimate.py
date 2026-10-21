from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class EstimateItem(BaseModel):
    name: str = Field(default="", max_length=200)
    unit_price: int = Field(default=0, ge=0, le=100_000_000)
    freight: int = Field(default=0, ge=0, le=100_000_000)
    quantity: int = Field(default=1, ge=1, le=10000)
    unit: str = Field(default="", max_length=20)
    internal_note: str = Field(default="", max_length=2000)

    @computed_field
    @property
    def subtotal(self) -> int:
        return self.unit_price * self.quantity + self.freight


class AccidentEstimateInput(BaseModel):
    store_name: str = Field(default="炬烽騎士精品", min_length=1, max_length=100)
    customer_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(default="", max_length=50)
    license_plate: str = Field(default="", max_length=30)
    vehicle_model: str = Field(default="", max_length=100)
    engine_number: str = Field(default="", max_length=100)
    estimate_date: date
    opened_date: date
    items: list[EstimateItem] = Field(default_factory=list, max_length=500)
    labor: int = Field(default=0, ge=0, le=100_000_000)
    estimator: str = Field(default="", max_length=100)
    terms: str = Field(default="本估價單經雙方簽章後生效，視同為買賣合約。\n估價單開發後如未在本店維修酌收費用為1500元整。", max_length=3000)
    internal_note: str = Field(default="", max_length=10000)


class AccidentEstimate(AccidentEstimateInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def total(self) -> int:
        return sum(item.subtotal for item in self.items) + self.labor
