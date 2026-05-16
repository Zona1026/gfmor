from db.database import Base, engine, SessionLocal
from db.models import SystemSetting
from dotenv import load_dotenv

def main():
    load_dotenv()
    print("正在更新資料庫架構 (建立 system_settings 表格)...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 初始設定資料
        initial_settings = [
            {"key": "store_name", "value": "炬烽騎士精品", "description": "商店名稱"},
            {"key": "store_address", "value": "高雄市某某區某某路123號", "description": "店面地址"},
            {"key": "store_phone", "value": "07-1234567", "description": "聯絡電話"},
            {"key": "business_hours", "value": "週一至週六 13:00 - 22:00", "description": "營業時間"},
            {"key": "footer_description", "value": "專業二輪維修、保養與精品改裝。提供最值得信賴的技術與服務。", "description": "頁尾描述"}
        ]
        
        for setting in initial_settings:
            existing = db.query(SystemSetting).filter(SystemSetting.key == setting["key"]).first()
            if not existing:
                new_setting = SystemSetting(**setting)
                db.add(new_setting)
                print(f"已新增設定: {setting['key']} = {setting['value']}")
            else:
                # 更新店名為新名稱
                if setting["key"] == "store_name":
                    existing.value = setting["value"]
                    print(f"已更新店名為: {setting['value']}")
                
        db.commit()
        print("系統設定初始化/更新完成！")
    except Exception as e:
        print(f"發生錯誤: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
