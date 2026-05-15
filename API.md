# API 文件

本文件紀錄系統中所有可用的 API 介面

---

## 商品 (Products)

管理商品資料的相關 API。

### 1. 建立新商品

- **Method:** `POST`
- **URL:** `/products/`
- **功能:** 傳入商品資料來建立一個新商品。
- **Request JSON 範例:**
  ```json
  {
    "name": "高效能煞車皮",
    "description": "適用於各種賽道環境的高性能煞車皮",
    "price": 2500,
    "stock": 50,
    "category": "煞車系統"
  }
  ```
- **Response JSON 範例 (成功):**
  ```json
  {
    "id": 1,
    "name": "高效能煞車皮",
    "description": "適用於各種賽道環境的高性能煞車皮",
    "price": 2500,
    "stock": 50,
    "category": "煞車系統"
  }
  ```

### 2. 讀取商品列表

- **Method:** `GET`
- **URL:** `/products/`
- **功能:** 讀取資料庫中的商品列表，可使用 `skip` 和 `limit` 參數進行分頁。
- **Request JSON 範例:**
  無
- **Response JSON 範例 (成功):**
  ```json
  [
    {
      "id": 1,
      "name": "高效能煞車皮",
      "description": "適用於各種賽道環境的高性能煞車皮",
      "price": 2500,
      "stock": 50,
      "category": "煞車系統"
    },
    {
      "id": 2,
      "name": "輕量化鍛造輪框",
      "description": "17吋輕量化輪框，提升操控性",
      "price": 18000,
      "stock": 20,
      "category": "輪框"
    }
  ]
  ```

### 3. 讀取單一商品

- **Method:** `GET`
- **URL:** `/products/{product_id}`
- **功能:** 根據商品 `product_id` 讀取單一商品的詳細資料。
- **Request JSON 範例:**
  無
- **Response JSON 範例 (成功):**
  ```json
  {
    "id": 1,
    "name": "高效能煞車皮",
    "description": "適用於各種賽道環境的高性能煞車皮",
    "price": 2500,
    "stock": 50,
    "category": "煞車系統"
  }
  ```
- **Response JSON 範例 (失敗):**
  ```json
  {
    "detail": "找不到該商品"
  }
  ```

### 4. 更新商品資訊

- **Method:** `PUT`
- **URL:** `/products/{product_id}`
- **功能:** 根據商品 `product_id` 更新商品的資訊，只需傳入想更新的欄位。
- **Request JSON 範例:**
  ```json
  {
    "price": 2800,
    "stock": 45
  }
  ```
- **Response JSON 範例 (成功):**
  ```json
  {
    "id": 1,
    "name": "高效能煞車皮",
    "description": "適用於各種賽道環境的高性能煞車皮",
    "price": 2800,
    "stock": 45,
    "category": "煞車系統"
  }
  ```

### 5. 刪除商品

- **Method:** `DELETE`
- **URL:** `/products/{product_id}`
- **功能:** 根據商品 `product_id` 刪除指定的商品。
- **Request JSON 範例:**
  無
- **Response JSON 範例 (成功):**
  ```json
  {
    "detail": "商品刪除成功"
  }
  ```

---

## 預約 (Bookings)

管理客戶服務預約的相關 API。

### 1. 建立新預約

- **Method:** `POST`
- **URL:** `/bookings/`
- **功能:** 傳入客戶、車輛及服務內容來建立一筆新的預約紀錄。
- **Request JSON 範例:**
  ```json
  {
    "google_id": "user-google-id-12345",
    "motor_id": 1,
    "booking_time": "2026-03-15T14:00:00",
    "category": "保養",
    "notes": "希望一併檢查胎壓。"
  }
  ```
- **Response JSON 範例 (成功):**
  ```json
  {
    "google_id": "user-google-id-12345",
    "motor_id": 1,
    "booking_time": "2026-03-15T14:00:00",
    "category": "保養",
    "notes": "希望一併檢查胎壓。",
    "id": 1,
    "created_at": "2026-02-12T12:00:00Z",
    "status": "預約中",
    "user": {
      "google_id": "user-google-id-12345",
      "name": "王大明",
      "phone": "0912345678"
    },
    "motor": {
      "id": 1,
      "license_plate": "ABC-1234",
      "model_name": "JETS"
    }
  }
  ```
- **Response JSON 範例 (失敗 - 驗證錯誤):**
  ```json
  {
    "detail": "車籍資料 (ID: 99) 與使用者 (Google ID: user-google-id-12345) 不匹配。"
  }
  ```

### 2. 讀取預約列表

- **Method:** `GET`
- **URL:** `/bookings/`
- **功能:** 讀取資料庫中的預約單列表，可使用 `skip` 和 `limit` 參數進行分頁。
- **Request JSON 範例:**
  無
- **Response JSON 範例 (成功):**
  ```json
  [
    {
      "google_id": "user-google-id-12345",
      "motor_id": 1,
      "booking_time": "2026-03-15T14:00:00",
      "category": "保養",
      "notes": "希望一併檢查胎壓。",
      "id": 1,
      "created_at": "2026-02-12T12:00:00Z",
      "status": "預約中",
      "user": {
        "google_id": "user-google-id-12345",
        "name": "王大明",
        "phone": "0912345678"
      },
      "motor": {
        "id": 1,
        "license_plate": "ABC-1234",
        "model_name": "JETS"
      }
    }
  ]
  ```

### 3. 讀取單一預約

- **Method:** `GET`
- **URL:** `/bookings/{booking_id}`
- **功能:** 根據 `booking_id` 讀取單一預約單的詳細資料。
- **Request JSON 範例:**
  無
- **Response JSON 範例 (成功):**
  同上方的單一預約物件。

### 4. 更新預約資訊

- **Method:** `PUT`
- **URL:** `/bookings/{booking_id}`
- **功能:** 根據 `booking_id` 更新預約單的狀態或備註。
- **Request JSON 範例:**
  ```json
  {
    "status": "已結案"
  }
  ```
- **Response JSON 範例 (成功):**
  ```json
  {
    "google_id": "user-google-id-12345",
    "motor_id": 1,
    "booking_time": "2026-03-15T14:00:00",
    "category": "保養",
    "notes": "希望一併檢查胎壓。",
    "id": 1,
    "created_at": "2026-02-12T12:00:00Z",
    "status": "已結案",
    "user": { ... },
    "motor": { ... }
  }
  ```

---

## 工單 (Work Orders)

管理維修或改裝工單的相關 API。

### 1. 建立新工單

- **Method:** `POST`
- **URL:** `/work-orders/`
- **功能:** 傳入一個既有的「來源預約單號」(booking_id) 和商品項目 (預約項目) 來建立一張新的工單。後端會自動檢查庫存並計算總價。
- **Request JSON 範例:**
  ```json
  {
    "booking_id": 1,
    "notes": "客戶要求更換後輪煞車皮，並檢查前輪。",
    "items": [
      {
        "product_id": 1,
        "quantity": 2
      },
      {
        "product_id": 2,
        "quantity": 1
      }
    ]
  }
  ```
- **Response JSON 範例 (成功):**
  ```json
  {
    "booking_id": 1,
    "notes": "客戶要求更換後輪煞車皮，並檢查前輪。",
    "id": 1,
    "status": "待處理",
    "total_amount": 23000,
    "created_at": "2026-02-12T10:00:00Z",
    "completed_at": null,
    "items": [
      {
        "product_id": 1,
        "quantity": 2,
        "id": 1,
        "unit_price": 2500,
        "product": {
          "id": 1,
          "name": "高效能煞車皮",
          "price": 2500
        }
      },
      {
        "product_id": 2,
        "quantity": 1,
        "id": 2,
        "unit_price": 18000,
        "product": {
          "id": 2,
          "name": "輕量化鍛造輪框",
          "price": 18000
        }
      }
    ]
  }
  ```
- **Response JSON 範例 (失敗 - 庫存不足):**
  ```json
  {
    "detail": "商品 '輕量化鍛造輪框' (ID: 2) 庫存不足。需要 1，但只有 0。"
  }
  ```

### 2. 讀取工單列表

- **Method:** `GET`
- **URL:** `/work-orders/`
- **功能:** 讀取資料庫中的工單列表，可使用 `skip` 和 `limit` 參數進行分頁。
- **Request JSON 範例:**
  無
- **Response JSON 範例 (成功):**
  ```json
  [
    {
      "booking_id": 1,
      "notes": "客戶要求更換後輪煞車皮，並檢查前輪。",
      "id": 1,
      "status": "待處理",
      "total_amount": 23000,
      "created_at": "2026-02-12T10:00:00Z",
      "completed_at": null,
      "items": [
        {
          "product_id": 1,
          "quantity": 2,
          "id": 1,
          "unit_price": 2500,
          "product": {
            "id": 1,
            "name": "高效能煞車皮",
            "price": 2500
          }
        }
      ]
    }
  ]
  ```

### 3. 讀取單一工單

- **Method:** `GET`
- **URL:** `/work-orders/{work_order_id}`
- **功能:** 根據 `work_order_id` 讀取單一工單的詳細資料。
- **Request JSON 範例:**
  無
- **Response JSON 範例 (成功):**
  ```json
  {
    "booking_id": 1,
    "notes": "客戶要求更換後輪煞車皮，並檢查前輪。",
    "id": 1,
    "status": "待處理",
    "total_amount": 23000,
    "created_at": "2026-02-12T10:00:00Z",
    "completed_at": null,
    "items": [
      {
        "product_id": 1,
        "quantity": 2,
        "id": 1,
        "unit_price": 2500,
        "product": {
          "id": 1,
          "name": "高效能煞車皮",
          "price": 2500
        }
      },
      {
        "product_id": 2,
        "quantity": 1,
        "id": 2,
        "unit_price": 18000,
        "product": {
          "id": 2,
          "name": "輕量化鍛造輪框",
          "price": 18000
        }
      }
    ]
  }
  ```

### 4. 更新工單資訊

- **Method:** `PUT`
- **URL:** `/work-orders/{work_order_id}`
- **功能:** 根據 `work_order_id` 更新工單的狀態或備註。
- **Request JSON 範例:**
  ```json
  {
    "status": "處理中",
    "notes": "已更換煞車皮，待料中。"
  }
  ```
- **Response JSON 範例 (成功):**
  ```json
  {
    "booking_id": 1,
    "notes": "已更換煞車皮，待料中。",
    "id": 1,
    "status": "處理中",
    "total_amount": 23000,
    "created_at": "2026-02-12T10:00:00Z",
    "completed_at": null,
    "items": [ ... ]
  }
  ```

---

## 使用者 (Users)

管理與查詢使用者資料的相關 API。

### 1. 依姓名模糊搜尋客戶

- **Method:** `GET`
- **URL:** `/users/search?name={name}`
- **功能:** 根據姓名關鍵字模糊搜尋客戶，回傳符合的使用者列表，包含其名下的車籍資料。用於在建立預約時，輔助查詢客戶的 Google ID 與車籍 ID。
- **Request JSON 範例:**
  無 (參數透過 URL query string 提供)
- **Response JSON 範例 (成功):**
  ```json
  [
    {
      "email": "ming@example.com",
      "name": "王大明",
      "phone": "0912345678",
      "google_id": "user-google-id-12345",
      "join_time": "2026-01-10T10:00:00Z",
      "membership_level": "VIP",
      "motors": [
        {
          "id": 1,
          "license_plate": "ABC-1234",
          "model_name": "JETS"
        }
      ]
    }
  ]
  ```

### 2. 建立測試用使用者

- **Method:** `POST`
- **URL:** `/users/`
- **功能:** 建立一筆測試用的使用者。後端會自動產生一組 `test-user-` 開頭的假 Google ID。此功能主要用於開發與測試階段。
- **Request JSON 範例:**
  ```json
  {
    "name": "林小美",
    "email": "mei@example.com"
  }
  ```
- **Response JSON 範例 (成功):**
  ```json
  {
    "email": "mei@example.com",
    "name": "林小美",
    "phone": null,
    "google_id": "test-user-1645000000",
    "join_time": "2026-02-16T12:00:00Z",
    "membership_level": null
  }
  ```

### 3. 讀取使用者列表

- **Method:** `GET`
- **URL:** `/users/`
- **功能:** 讀取資料庫中的使用者列表。
- **Request JSON 範例:**
  無
- **Response JSON 範例 (成功):**
  ```json
  [
    {
      "email": "ming@example.com",
      "name": "王大明",
      "phone": "0912345678",
      "google_id": "user-google-id-12345",
      "join_time": "2026-01-10T10:00:00Z",
      "membership_level": "VIP"
    }
  ]
  ```

### 4. 讀取單一使用者

- **Method:** `GET`
- **URL:** `/users/{google_id}`
- **功能:** 根據 `google_id` 讀取單一使用者的詳細資料，包含其名下的所有車輛。
- **Request JSON 範例:**
  無
- **Response JSON 範例 (成功):**
  同「依姓名模糊搜尋客戶」的回應範例中的單一使用者物件。

### 5. 更新使用者資訊

- **Method:** `PUT`
- **URL:** `/users/{google_id}`
- **功能:** 根據 `google_id` 更新該使用者的資訊 (例如：姓名、電話、會員等級)。
- **Request JSON 範例:**
  ```json
  {
    "phone": "0987654321",
    "membership_level": "白金會員"
  }
  ```
- **Response JSON 範例 (成功):**
  ```json
  {
    "email": "ming@example.com",
    "name": "王大明",
    "phone": "0987654321",
    "google_id": "user-google-id-12345",
    "join_time": "2026-01-10T10:00:00Z",
    "membership_level": "白金會員"
  }
  ```

### 6. 刪除使用者

- **Method:** `DELETE`
- **URL:** `/users/{google_id}`
- **功能:** 根據 `google_id` 刪除使用者。如果該使用者尚有關聯紀錄，將會刪除失敗。
- **Request JSON 範例:**
  無
- **Response JSON 範例 (成功):**
  無內容 (HTTP 204 No Content)
- **Response JSON 範例 (失敗):**
  ```json
  {
    "detail": "無法刪除使用者 '王大明' (ID: user-google-id-12345)，因為該使用者尚有關聯的車籍、預約或訂單紀錄。"
  }
  ```

