# test_db.py
import pymysql

try:
    # 嘗試直接連線，不透過 SQLAlchemy
    # 請記得改你的密碼
    connection = pymysql.connect(
        host='gfmotor-gfmotor001.j.aivencloud.com',
        user='avnadmin',
        password='AVNS_wpMgWFawTeSbnCOGuxo', 
        database='gfmotor',
        port=12676
    )
    print("✅ 恭喜！資料庫連線成功！(pymysql 運作正常)")
    connection.close()
except Exception as e:
    print("❌ 連線失敗！原因如下：")
    print(e)