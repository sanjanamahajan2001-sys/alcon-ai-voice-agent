import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env"))
load_dotenv(dotenv_path)

print(f"Connecting to database {os.getenv('DB_NAME')} on {os.getenv('DB_HOST')}...")

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT")
    )
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Query calls
    print("\n--- Calls ---")
    cursor.execute("SELECT * FROM calls WHERE customer_id IN ('1', '14', '17');")
    calls = cursor.fetchall()
    print(f"Calls found: {len(calls)}")
    for call in calls:
        print(call)
        
    # 2. Query lead_states
    print("\n--- Lead States ---")
    cursor.execute("""
        SELECT ls.*, c.customer_id, c.status as call_status 
        FROM lead_states ls
        JOIN calls c ON ls.call_sid = c.call_sid
        WHERE c.customer_id IN ('1', '14', '17');
    """)
    target_leads = cursor.fetchall()
    print(f"Lead states found: {len(target_leads)}")
    for lead in target_leads:
        print(lead)

    # 3. Query campaign_queue
    print("\n--- Campaign Queue ---")
    cursor.execute("SELECT * FROM campaign_queue WHERE customer_id IN ('1', '14', '17');")
    q_items = cursor.fetchall()
    print(f"Queue items found: {len(q_items)}")
    for item in q_items:
        print(item)
        
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Database error: {e}")
