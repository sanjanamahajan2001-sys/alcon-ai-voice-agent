import sys
sys.path.append('.')
from database import DatabaseManager
from flow_manager import SessionManager # wait, check where SessionManager is defined
# let's grep or import from flow_manager
from flow_manager import FlowManager

db = DatabaseManager()
fm = FlowManager(db)
session = fm.session_manager.get_session("DEBUG_CALL_12345")
print("Session:", session)

customer = fm.get_customer("12")
print("Customer:", customer)

lead = db.get_lead_state("DEBUG_CALL_12345")
print("Lead State:", lead)
