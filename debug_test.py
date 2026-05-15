import sys
import os
import json
sys.path.append(os.getcwd())

from db.database import SessionLocal
from db import models
from sqlalchemy import text

def test_data():
    db = SessionLocal()
    results = {}
    
    try:
        # Check Bookings
        bookings_data = db.query(models.Booking).all()
        results['bookings_count'] = len(bookings_data)
        results['bookings_sample'] = [f"ID:{b.id}, Status:{b.status}" for b in bookings_data[:5]]
    except Exception as e:
        results['bookings_error'] = str(e)

    try:
        # Check Orders
        orders_data = db.query(models.Order).all()
        results['orders_count'] = len(orders_data)
        results['orders_sample'] = [f"ID:{o.id}, Status:{o.status}, Source:{o.source}" for o in orders_data[:5]]
    except Exception as e:
        results['orders_error'] = str(e)

    # Check DB structure
    with db.bind.connect() as conn:
        for table in ['bookings', 'orders', 'users']:
            try:
                res = conn.execute(text(f"SHOW COLUMNS FROM {table}"))
                results[f'{table}_columns'] = [dict(row._mapping) for row in res]
                
                res = conn.execute(text(f"SELECT DISTINCT status FROM {table}"))
                results[f'{table}_distinct_status'] = [str(row[0]) for row in res]
            except Exception as e:
                results[f'{table}_info_error'] = str(e)

    db.close()
    with open('debug_results_final.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Results saved to debug_results_final.json")

if __name__ == "__main__":
    test_data()
