import sqlite3
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables explicitly for DB initialization
load_dotenv()

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

DB_PATH = "data/alcon.db"

# Database initialization is now managed within the DatabaseManager class.

_DB_INITIALIZED = False

class DatabaseManager:
    # Standardized Conversation Outcomes
    OUTCOME_HOT_TRANSFERRED = "HOT_TRANSFERRED"
    OUTCOME_HOT_CALLBACK = "HOT_CALLBACK"
    OUTCOME_WARM_NURTURE = "WARM_NURTURE"
    OUTCOME_COLD_DECLINED = "COLD_DECLINED"
    OUTCOME_SERVICE_REDIRECTED = "SERVICE_REDIRECTED"
    OUTCOME_DND = "DND"
    OUTCOME_INVALID_LEAD = "INVALID_LEAD"

    def __init__(self):
        global _DB_INITIALIZED
        self.engine = "postgres" if POSTGRES_AVAILABLE and os.getenv("DB_HOST") else "sqlite"
        if not _DB_INITIALIZED:
            self.init_db()
            _DB_INITIALIZED = True
        self.last_op_time = 0
        self.placeholder = "%s" if self.engine == "postgres" else "?"

    def _get_conn(self):
        t_start = time.time()
        if self.engine == "postgres":
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASS"),
                port=os.getenv("DB_PORT")
            )
        else:
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL")
        self.last_op_time = time.time() - t_start
        return conn

    def get_cursor(self, conn):
        """Returns a dictionary cursor based on the current engine."""
        if self.engine == "postgres":
            from psycopg2.extras import RealDictCursor
            return conn.cursor(cursor_factory=RealDictCursor)
        else:
            conn.row_factory = sqlite3.Row
            return conn.cursor()

    def execute_query(self, query, params=(), fetch=False):
        """Standardized query execution with connection management."""
        # Normalize placeholders for SQLite
        if self.engine == "sqlite":
            query = query.replace("%s", "?")
            
        conn = self._get_conn()
        try:
            cursor = self.get_cursor(conn)
            cursor.execute(query, params)
            if fetch:
                res = cursor.fetchall()
                # Convert SQLite Row objects to dicts
                if self.engine == "sqlite":
                    return [dict(row) for row in res]
                return res
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def fetch_one(self, query, params=()):
        """Fetch a single record from the database."""
        if self.engine == "sqlite":
            query = query.replace("%s", "?")
        conn = self._get_conn()
        try:
            cursor = self.get_cursor(conn)
            cursor.execute(query, params)
            res = cursor.fetchone()
            if self.engine == "sqlite" and res:
                return dict(res)
            return res
        finally:
            conn.close()

    def _record_time(self, start_time):
        self.last_op_time = time.time() - start_time

    def create_call(self, call_sid, customer_id, campaign_id=None, idempotency_key=None, **kwargs):
        t_start = time.time()
        conn = self._get_conn()
        cursor = conn.cursor()
        p = self.placeholder
        try:
            cursor.execute(f'''
                INSERT INTO calls (call_sid, customer_id, campaign_id, idempotency_key, stage, last_contacted_at)
                VALUES ({p}, {p}, {p}, {p}, {p}, {p})
            ''', (call_sid, customer_id, campaign_id, idempotency_key, kwargs.get('stage'), datetime.now().isoformat()))
            
            cursor.execute(f'''
                INSERT INTO lead_states (call_sid)
                VALUES ({p})
            ''', (call_sid,))
            
            conn.commit()
            self._record_time(t_start)
            return True
        except Exception:
            self._record_time(t_start)
            return False
        finally:
            conn.close()

    def update_call_status(self, call_sid, status, customer_id="Unknown", stage=None):
        t_start = time.time()
        conn = self._get_conn()
        cursor = conn.cursor()
        p = self.placeholder
        
        cursor.execute(f"SELECT 1 FROM calls WHERE call_sid = {p}", (call_sid,))
        if not cursor.fetchone():
            self.create_call(call_sid, customer_id, stage=stage)
        
        if stage is not None:
            cursor.execute(f"UPDATE calls SET status = {p}, stage = {p}, last_contacted_at = {p} WHERE call_sid = {p}", 
                          (status, stage, datetime.now().isoformat(), call_sid))
        else:
            cursor.execute(f"UPDATE calls SET status = {p}, last_contacted_at = {p} WHERE call_sid = {p}", 
                          (status, datetime.now().isoformat(), call_sid))
        conn.commit()
        conn.close()
        self._record_time(t_start)

    def increment_retry_count(self, call_sid):
        t_start = time.time()
        conn = self._get_conn()
        cursor = conn.cursor()
        p = self.placeholder
        cursor.execute(f'''
            UPDATE calls 
            SET retry_count = retry_count + 1, last_contacted_at = {p}
            WHERE call_sid = {p}
        ''', (datetime.now().isoformat(), call_sid))
        conn.commit()
        conn.close()
        self._record_time(t_start)

    def update_lead_state(self, call_sid, **kwargs):
        if not kwargs: return
        t_start = time.time()
        conn = self._get_conn()
        cursor = conn.cursor()
        p = self.placeholder
        
        try:
            print(f"[DB] Updating Lead State for {call_sid}: {kwargs}")
            
            # Robust UPSERT
            if self.engine == "postgres":
                cursor.execute("""
                    INSERT INTO lead_states (call_sid) VALUES (%s)
                    ON CONFLICT (call_sid) DO NOTHING
                """, (call_sid,))
            else:
                cursor.execute(f"INSERT OR IGNORE INTO lead_states (call_sid) VALUES (?)", (call_sid,))
        
            fields = []
            values = []
            for key, value in kwargs.items():
                fields.append(f"{key} = {p}")
                values.append(json.dumps(value) if isinstance(value, (dict, list)) else value)
        
            if fields:
                values.append(call_sid)
                query = f"UPDATE lead_states SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE call_sid = {p}"
                cursor.execute(query, values)
                print(f"[DB] Updated {cursor.rowcount} rows in lead_states")
                
            if "lead_status" in kwargs:
                cursor.execute(f"UPDATE call_logs SET outcome = {p} WHERE call_sid = {p}", (kwargs["lead_status"], call_sid))
                
            conn.commit()
        except Exception as e:
            print(f"[DB ERROR] update_lead_state failed: {e}")
            if conn: conn.rollback()
        finally:
            if conn: conn.close()
            self._record_time(t_start)

    def init_db(self):
        """Initialize all required tables for the orchestrator."""
        id_type = "SERIAL PRIMARY KEY" if self.engine == "postgres" else "INTEGER PRIMARY KEY AUTOINCREMENT"
        
        tables = [
            f'''CREATE TABLE IF NOT EXISTS calls (
                call_sid TEXT PRIMARY KEY,
                idempotency_key TEXT UNIQUE,
                campaign_id TEXT,
                customer_id TEXT,
                status TEXT DEFAULT 'initiated',
                retry_count INTEGER DEFAULT 0,
                stage INTEGER,
                last_contacted_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            f'''CREATE TABLE IF NOT EXISTS lead_states (
                call_sid TEXT PRIMARY KEY,
                lead_status TEXT,
                lead_score INTEGER DEFAULT 0,
                disposition TEXT,
                last_action TEXT,
                next_step TEXT,
                interest_level TEXT,
                follow_up_time TEXT,
                service_linked BOOLEAN DEFAULT FALSE,
                whatsapp_sent_at TEXT,
                reasoning_trace TEXT,
                policy_status TEXT,
                priority_score INTEGER DEFAULT 0,
                escalation_status TEXT DEFAULT 'NONE',
                human_agent_id TEXT,
                pending_updates TEXT,
                escalation_reason TEXT,
                car VARCHAR(100),
                car_model VARCHAR(100),
                feedback_score INTEGER DEFAULT NULL,
                feedback_text TEXT DEFAULT NULL,
                memory JSONB DEFAULT '{{}}',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            f'''CREATE TABLE IF NOT EXISTS call_logs (
                id {id_type},
                call_sid TEXT,
                customer_id TEXT,
                stage INTEGER,
                transcript TEXT,
                outcome TEXT,
                fallback_triggered BOOLEAN DEFAULT FALSE,
                confidence_score FLOAT DEFAULT 1.0,
                compliance_status TEXT DEFAULT 'PENDING',
                audit_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            f'''CREATE TABLE IF NOT EXISTS consent_logs (
                id {id_type},
                call_sid TEXT,
                customer_id TEXT,
                consent_type TEXT,
                granted BOOLEAN,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            f'''CREATE TABLE IF NOT EXISTS scheduled_followups (
                id {id_type},
                customer_id TEXT,
                call_sid TEXT,
                scheduled_at TIMESTAMP,
                status TEXT DEFAULT 'PENDING'
            )''',
            f'''CREATE TABLE IF NOT EXISTS orchestration_audit (
                id {id_type},
                call_sid TEXT,
                previous_node TEXT,
                current_node TEXT,
                trigger_reason TEXT,
                raw_input TEXT,
                resolved_intent TEXT,
                confidence_score FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            f'''CREATE TABLE IF NOT EXISTS campaign_queue (
                id {id_type},
                customer_id TEXT,
                customer_name TEXT,
                car_model TEXT,
                flow_type TEXT,
                status TEXT DEFAULT 'queued',
                log_text TEXT DEFAULT '',
                telephony_sid TEXT,
                active_node TEXT,
                progress_percent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )'''
        ]

        for table_sql in tables:
            try:
                # Simple dialect adjustment for IDs if SQLite
                if self.engine == "sqlite":
                    table_sql = table_sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                    table_sql = table_sql.replace("TIMESTAMP", "DATETIME")
                    table_sql = table_sql.replace("FALSE", "0").replace("TRUE", "1")
                
                self.execute_query(table_sql)
            except Exception as e:
                print(f"[DB ERROR] Table creation failed: {e}")
        
        # Self-Migration: Ensure newer columns exist for stateful orchestration
        self.ensure_columns_exist()
        print("✅ Database initialized and schema verified.")

    def ensure_columns_exist(self):
        """Programmatically add missing columns to existing tables."""
        migrations = [
            ("lead_states", "car", "TEXT"),
            ("lead_states", "car_model", "TEXT"),
            ("lead_states", "memory", "JSONB DEFAULT '{}'"),
            ("lead_states", "feedback_score", "INTEGER DEFAULT NULL"),
            ("lead_states", "feedback_text", "TEXT DEFAULT NULL")
        ]
        
        for table, column, col_type in migrations:
            try:
                # Check if column exists
                if self.engine == "postgres":
                    check_sql = f"""
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='{table}' AND column_name='{column}';
                    """
                else:
                    # SQLite: Use PRAGMA table_info
                    check_sql = f"PRAGMA table_info({table});"
                
                exists = False
                if self.engine == "postgres":
                    exists = self.fetch_one(check_sql)
                else:
                    res = self.execute_query(check_sql, fetch=True)
                    exists = any(row['name'] == column for row in res)

                if not exists:
                    print(f"🚀 Migrating: Adding {column} to {table}...")
                    self.execute_query(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};")
            except Exception as e:
                print(f"[MIGRATION ERROR] Failed to add {column} to {table}: {e}")

    def log_call_history(self, call_sid, customer_id, stage, transcript, outcome, fallback=False, confidence=1.0, compliance="PENDING", audit_summary=None):
        t_start = time.time()
        conn = self._get_conn()
        cursor = conn.cursor()
        p = self.placeholder
        cursor.execute(f'''
            INSERT INTO call_logs (call_sid, customer_id, stage, transcript, outcome, fallback_triggered, confidence_score, compliance_status, audit_summary)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
        ''', (call_sid, customer_id, stage, json.dumps(transcript), outcome, fallback, confidence, compliance, json.dumps(audit_summary) if audit_summary else None))
        conn.commit()
        conn.close()
        self._record_time(t_start)

    def get_call_data(self, call_sid):
        conn = self._get_conn()
        cursor = self.get_cursor(conn)
        p = self.placeholder
        cursor.execute(f'''
            SELECT c.*, l.interest_level, l.follow_up_time, l.service_linked, l.whatsapp_sent_at, l.reasoning_trace
            FROM calls c
            LEFT JOIN lead_states l ON c.call_sid = l.call_sid
            WHERE c.call_sid = {p}
        ''', (call_sid,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_sid_by_idempotency_key(self, key):
        conn = self._get_conn()
        cursor = conn.cursor()
        p = self.placeholder
        cursor.execute(f'SELECT call_sid FROM calls WHERE idempotency_key = {p}', (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def get_lead_state(self, call_sid):
        conn = self._get_conn()
        if self.engine == "postgres":
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        p = self.placeholder
        cursor.execute(f"SELECT * FROM lead_states WHERE call_sid = {p}", (call_sid,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # --- NEW METHODS FOR PRODUCTION WORKER ---
    def get_active_call_for_customer(self, customer_id):
        conn = self._get_conn()
        if self.engine == "postgres":
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        p = self.placeholder
        cursor.execute(f"SELECT * FROM calls WHERE customer_id = {p} AND status NOT IN ('completed', 'failed', 'busy', 'no-answer') LIMIT 1", (customer_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_pending_retries(self):
        conn = self._get_conn()
        if self.engine == "postgres":
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        p = self.placeholder
        # Find calls that are failed/no-answer but haven't reached max retries
        # For simplicity in this mock, we look for 'initiated' status that haven't been updated in a while
        cursor.execute(f"SELECT * FROM calls WHERE status IN ('failed', 'no-answer', 'busy') AND retry_count < 3")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_pending_followups(self):
        conn = self._get_conn()
        if self.engine == "postgres":
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        p = self.placeholder
        cursor.execute(f"SELECT * FROM scheduled_followups WHERE status = 'pending'")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def mark_followup_complete(self, followup_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        p = self.placeholder
        cursor.execute(f"UPDATE scheduled_followups SET status = 'completed' WHERE id = {p}", (followup_id,))
        conn.commit()
        conn.close()

    def log_consent(self, call_sid, customer_id, consent_type, granted):
        """Log IRDAI compliance consent."""
        t_start = time.time()
        conn = self._get_conn()
        cursor = conn.cursor()
        p = self.placeholder
        cursor.execute(f'''
            INSERT INTO consent_logs (call_sid, customer_id, consent_type, granted)
            VALUES ({p}, {p}, {p}, {p})
        ''', (call_sid, customer_id, consent_type, granted))
        conn.commit()
        conn.close()
        self._record_time(t_start)

    def cancel_followup(self, customer_id):
        """Cancel all pending followups for a customer."""
        t_start = time.time()
        conn = self._get_conn()
        cursor = conn.cursor()
        p = self.placeholder
        cursor.execute(f"UPDATE scheduled_followups SET status = 'cancelled' WHERE customer_id = {p}", (customer_id,))
        conn.commit()
        conn.close()
        self._record_time(t_start)

    def schedule_followup(self, customer_id, call_sid, scheduled_time):
        """Schedule a new followup call."""
        t_start = time.time()
        conn = self._get_conn()
        cursor = conn.cursor()
        p = self.placeholder
        # Use a unique job_key to prevent duplicates (call_sid + time)
        job_key = f"{call_sid}_{scheduled_time}"
        try:
            cursor.execute(f'''
                INSERT INTO scheduled_followups (customer_id, call_sid, scheduled_time, job_key, status)
                VALUES ({p}, {p}, {p}, {p}, 'pending')
                ON CONFLICT (job_key) DO NOTHING
            ''', (customer_id, call_sid, scheduled_time, job_key))
            conn.commit()
        except Exception as e:
            # Fallback for SQLite which might not support ON CONFLICT the same way depending on version
            if "UNIQUE constraint failed" in str(e):
                pass
            else:
                print(f"[DB ERROR] schedule_followup failed: {e}")
            conn.close()
            self._record_time(t_start)

    def enqueue_campaign_job(self, customer_id, customer_name, car_model, flow_type):
        t_start = time.time()
        conn = self._get_conn()
        cursor = conn.cursor()
        p = self.placeholder
        try:
            cursor.execute(f'''
                INSERT INTO campaign_queue (customer_id, customer_name, car_model, flow_type, status, progress_percent)
                VALUES ({p}, {p}, {p}, {p}, 'queued', 0)
            ''', (customer_id, customer_name, car_model, flow_type))
            conn.commit()
            self._record_time(t_start)
            return True
        except Exception as e:
            print(f"[DB ERROR] enqueue_campaign_job failed: {e}")
            self._record_time(t_start)
            return False
        finally:
            conn.close()

    def get_queued_jobs(self):
        conn = self._get_conn()
        cursor = self.get_cursor(conn)
        cursor.execute("SELECT * FROM campaign_queue ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def clear_campaign_queue(self):
        t_start = time.time()
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM campaign_queue")
        conn.commit()
        conn.close()
        self._record_time(t_start)
        return True

    def retrigger_campaign_job(self, job_id):
        t_start = time.time()
        conn = self._get_conn()
        cursor = conn.cursor()
        p = self.placeholder
        cursor.execute(f'''
            UPDATE campaign_queue
            SET status = 'queued', active_node = NULL, progress_percent = 0, log_text = '', updated_at = CURRENT_TIMESTAMP
            WHERE id = {p}
        ''', (job_id,))
        conn.commit()
        conn.close()
        self._record_time(t_start)
        return True

    def update_campaign_job_status(self, job_id, status, progress_percent=None, active_node=None, log_text=None):
        t_start = time.time()
        conn = self._get_conn()
        cursor = conn.cursor()
        p = self.placeholder
        
        updates = [f"status = {p}", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        
        if progress_percent is not None:
            updates.append(f"progress_percent = {p}")
            params.append(progress_percent)
            
        if active_node is not None:
            updates.append(f"active_node = {p}")
            params.append(active_node)
            
        if log_text is not None:
            updates.append(f"log_text = {p}")
            params.append(log_text)
            
        params.append(job_id)
        
        query = f"UPDATE campaign_queue SET {', '.join(updates)} WHERE id = {p}"
        
        try:
            cursor.execute(query, params)
            conn.commit()
        except Exception as e:
            print(f"[DB ERROR] update_campaign_job_status failed: {e}")
        finally:
            conn.close()
            self._record_time(t_start)

if __name__ == "__main__":
    init_db()
