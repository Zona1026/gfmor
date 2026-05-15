from db.database import Base, engine
from db import models
from dotenv import load_dotenv

def main():
    """
    主函式，用於建立資料庫表格。
    """
    load_dotenv()
    print("正在初始化資料庫，準備建立所有表格...")
    
    # Base.metadata.create_all() 會檢查所有繼承自 Base 的 class (在 models.py 中定義)
    # 並在資料庫中建立對應的表格。
    # 如果表格已存在，此指令不會重複建立。
    Base.metadata.create_all(bind=engine)
    
    print("資料庫表格建立完成！")
    print("現在您可以執行 'uvicorn main:app --reload' 來啟動伺服器。")

if __name__ == "__main__":
    main()
