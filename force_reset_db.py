# force_reset_db.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
from db.database import Base, engine
from db import models

def main():
    print("Loading .env file...")
    load_dotenv()
    print(".env loaded.")
    
    print("--- WARNING: This will delete all data in the database! ---")
    
    try:
        print("Attempting to drop all tables...")
        Base.metadata.drop_all(bind=engine)
        print("Tables dropped successfully.")
    except Exception as e:
        print(f"An error occurred while dropping tables: {e}")

    try:
        print("Attempting to create all tables...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully.")
    except Exception as e:
        print(f"An error occurred while creating tables: {e}")
        return

    print("\nDatabase reset complete.")
    print("You may now start the server with 'uvicorn main:app --reload'")

if __name__ == "__main__":
    main()
