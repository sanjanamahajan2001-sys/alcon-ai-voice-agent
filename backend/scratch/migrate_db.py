import os
import sys
sys.path.append(os.getcwd())
from database import DatabaseManager

def migrate():
    db = DatabaseManager()
    print("🚀 Starting Database Migration...")
    
    # Check and Add 'car' column
    try:
        db.execute_query("ALTER TABLE lead_states ADD COLUMN car TEXT;")
        print("✅ Added 'car' column.")
    except Exception as e:
        print(f"⚠️ 'car' column probably exists: {e}")

    # Check and Add 'car_model' column
    try:
        db.execute_query("ALTER TABLE lead_states ADD COLUMN car_model TEXT;")
        print("✅ Added 'car_model' column.")
    except Exception as e:
        print(f"⚠️ 'car_model' column probably exists: {e}")

    # Check and Add 'memory' column
    try:
        db.execute_query("ALTER TABLE lead_states ADD COLUMN memory JSONB DEFAULT '{}';")
        print("✅ Added 'memory' column.")
    except Exception as e:
        print(f"⚠️ 'memory' column probably exists: {e}")

    print("🏁 Migration Complete.")

if __name__ == "__main__":
    migrate()
