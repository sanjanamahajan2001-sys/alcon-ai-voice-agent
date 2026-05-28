import json
import os
import sqlite3
from datetime import datetime, date, timedelta
from database import DatabaseManager

class CampaignOrchestrator:
    def __init__(self, customers_file="data/customers.json"):
        self.customers_file = customers_file
        self.db = DatabaseManager()
        self.ALLOWED_START_HOUR = 9
        self.ALLOWED_END_HOUR = 20

    def _is_quiet_hours(self):
        if os.getenv("DEBUG_MODE") == "true":
            return False
        now = datetime.now()
        return not (self.ALLOWED_START_HOUR <= now.hour < self.ALLOWED_END_HOUR)

    def _calculate_stage(self, expiry_date_str):
        try:
            expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
            today = date.today()
            days_to_expiry = (expiry_date - today).days

            if days_to_expiry <= -1 and days_to_expiry >= -3:
                return 5 # Post-Expiry Recovery
            if days_to_expiry == 1:
                return 4 # Urgent
            if days_to_expiry <= 7 and days_to_expiry > 1:
                return 3 # Final Reminder
            if days_to_expiry <= 15 and days_to_expiry > 7:
                return 2 # Follow-up
            if days_to_expiry <= 30 and days_to_expiry > 15:
                return 1 # Initial
            return None
        except:
            return None

    def run_daily_sync(self):
        """Scans customers and schedules calls for the appropriate stage."""
        print(f"\n[ORCHESTRATOR] Starting Daily Sync at {datetime.now().isoformat()}")
        
        if self._is_quiet_hours():
            print("[ORCHESTRATOR] Currently in Quiet Hours. Rescheduling sync for later.")
            return

        try:
            with open(self.customers_file, "r") as f:
                customers = json.load(f)
        except Exception as e:
            print(f"[ORCHESTRATOR] Error loading customers: {e}")
            return

        for customer in customers:
            if not customer.get("insurance_expiry_date"):
                continue

            # 1. Respect DND
            if customer.get("dnd_status"):
                continue

            # 2. Check if already RENEWED
            if customer.get("policy_status") == "RENEWED":
                continue

            stage = self._calculate_stage(customer["insurance_expiry_date"])
            if not stage:
                continue

            # 3. Idempotency Check (job_key = customer_id_stage_year)
            current_year = date.today().year
            job_key = f"{customer['id']}_stage{stage}_{current_year}"
            
            # 4. Priority Score Calculation
            # Priority = (6 - stage) * 10 (Higher stage = Higher priority)
            # Adjust if Interested (would require checking DB)
            priority = (stage) * 20 

            # 5. Schedule in DB
            scheduled_time = datetime.now().isoformat() # For POC, schedule immediately
            
            conn = self.db._get_conn()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO scheduled_followups (customer_id, job_key, scheduled_time, status)
                    VALUES (?, ?, ?, ?)
                ''', (customer['id'], job_key, scheduled_time, 'pending'))
                conn.commit()
                print(f"[ORCHESTRATOR] Scheduled Stage {stage} for {customer['name']} (Key: {job_key})")
            except sqlite3.IntegrityError:
                # Already scheduled
                pass
            finally:
                conn.close()

if __name__ == "__main__":
    orchestrator = CampaignOrchestrator()
    orchestrator.run_daily_sync()
