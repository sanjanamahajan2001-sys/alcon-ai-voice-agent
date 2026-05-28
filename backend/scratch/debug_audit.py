import sqlite3

def check_audit():
    conn = sqlite3.connect("data/alcon.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- ORCHESTRATION AUDIT LOGS FOR SIM_CALL_12345 ---")
    cursor.execute("SELECT * FROM orchestration_audit WHERE call_sid = 'SIM_CALL_12345' ORDER BY id ASC")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row['id']} | Prev: {row['previous_node']} | Curr: {row['current_node']} | Reason: {row['trigger_reason']} | Input: '{row['raw_input']}' | Intent: {row['resolved_intent']}")
        
    print("\n--- LEAD STATE ---")
    cursor.execute("SELECT * FROM lead_states WHERE call_sid = 'SIM_CALL_12345'")
    row = cursor.fetchone()
    if row:
        print(dict(row))
        
    conn.close()

if __name__ == "__main__":
    check_audit()
