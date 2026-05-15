# 引入 Pydantic 的基礎模型和其他必要類型
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# 引入資料庫模型中定義的 Enum，以便在 Pydantic 模型中使用
from db.models import WorkOrderStatus

# --- 內部使用的輕量級 Schema ---
# 為了在 WorkOrderItem 中顯示關聯的商品資訊，但又不想造成循環依賴
# 我們在這裡定義一個輕量的 Product schema，只包含必要的回傳欄位。

class Product(BaseModel):
    """
    一個輕量級的商品 Schema，專門用於在其他 Schema 中作為巢狀回傳。
    例如，在工單項目中顯示商品的 id、名稱和價格。
    """
    id: int
    name: str
    price: int

    # 讓 Pydantic 可以從 ORM 物件屬性來讀取資料
    class Config:
        from_attributes = True

# --- 工單項目 (WorkOrderItem) 的 Schemas ---

class WorkOrderItemBase(BaseModel):
    """
    工單項目的基礎 Schema，定義了所有工單項目共用的欄位。
    """
    # 這個項目對應到哪個商品 (product) 的 ID
    product_id: int
    # 這個商品被使用了多少數量
    quantity: int

class WorkOrderItemCreate(WorkOrderItemBase):
    """
    用於「建立」工單項目時的 Schema。
    前端在建立一張新工單時，會傳入一個包含此結構的陣列。
    unit_price (單價) 不需要由客戶端提供，應由後端在建立時從商品資料庫抓取，以確保價格的準確性。
    """
    pass

class WorkOrderItem(WorkOrderItemBase):
    """
    用於「讀取」或「回傳」工單項目時的 Schema。
    它會包含資料庫生成的 id、當時的單價，以及完整的商品資訊。
    """
    # 工單項目的唯一流水號
    id: int
    # 執行當下的商品單價 (由後端寫入)
    unit_price: int
    # 巢狀顯示這個項目關聯的商品完整資訊
    product: Product

    # 讓 Pydantic 可以從 ORM 物件屬性來讀取資料
    class Config:
        from_attributes = True

# --- 工單 (WorkOrder) 的 Schemas ---

class WorkOrderBase(BaseModel):
    """
    工單的基礎 Schema，定義了所有工單共用的欄位。
    """
    # 這張工單是從哪一張預約單 (booking) 來的
    booking_id: int
    # 關於此工單的內部備註
    notes: Optional[str] = None

class WorkOrderCreate(BaseModel):
    """
    用於「建立」一張新工單的 Schema。
    這個結構是前端需要發送到 POST /work_orders 的資料格式。
    """
    # 關聯的預約單 ID
    booking_id: int
    # 內部備註
    notes: Optional[str] = None
    # 一個包含所有要建立的工單項目的列表
    items: List[WorkOrderItemCreate]

class WorkOrderUpdate(BaseModel):
    """
    用於「更新」一張工單時的 Schema。
    通常只允許更新狀態或備註等欄位。
    所有欄位都設為可選 (Optional)，因為更新時可能只會更新其中一部分。
    """
    # 要更新成的狀態
    status: Optional[WorkOrderStatus] = None
    # 要更新的備註
    notes: Optional[str] = None

class WorkOrder(WorkOrderBase):
    """
    用於「讀取」或「回傳」一張完整工單資訊的 Schema。
    這是 API GET /work_orders/{id} 的主要回傳格式。
    """
    # 工單的唯一流水號
    id: int
    # 工單目前的狀態
    status: WorkOrderStatus
    # 工單的總金額 (由後端計算)
    total_amount: int
    # 工單建立時間
    created_at: datetime
    # 工單完成時間 (如果還沒完成，此欄位為 null)
    completed_at: Optional[datetime] = None
    # 巢狀顯示這張工單包含的所有項目詳情
    items: List[WorkOrderItem] = []

    # 讓 Pydantic 可以從 ORM 物件屬性來讀取資料
    class Config:
        from_attributes = True
