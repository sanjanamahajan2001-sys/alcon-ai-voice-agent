from abc import ABC, abstractmethod
import json
import os

class BaseDMSAdapter(ABC):
    """
    Abstract contract defining production-grade DMS integrations.
    Any new dealer software connector (SAP, Salesforce, Oracle DMS) 
    must implement this interface.
    """
    
    @abstractmethod
    def fetch_customers(self):
        """Fetch all customer records from DMS database."""
        pass
        
    @abstractmethod
    def update_customer_state(self, customer_id: str, updates: dict) -> bool:
        """Sync back campaign triggers and final conversational outcomes to DMS."""
        pass


class LocalJSONDMSAdapter(BaseDMSAdapter):
    """
    Local JSON mock implementation wrapping data/customers.json.
    Provides seamless read/write fallback layer for demo phase.
    """
    
    def __init__(self, file_path="data/customers.json"):
        # Handle execution environments: backend dir or workspace root
        if not os.path.exists(file_path) and os.path.exists("poc/backend/" + file_path):
            self.file_path = "poc/backend/" + file_path
        else:
            self.file_path = file_path

    def fetch_customers(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[DMS ADAPTER ERROR] Failed to fetch customer file: {e}")
            return []

    def update_customer_state(self, customer_id: str, updates: dict) -> bool:
        try:
            customers = self.fetch_customers()
            updated = False
            for customer in customers:
                if str(customer.get("id")) == str(customer_id):
                    for key, val in updates.items():
                        customer[key] = val
                    updated = True
                    break
            
            if updated:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(customers, f, indent=4)
                print(f"✅ [DMS ADAPTER] Updated customer {customer_id} in {self.file_path}: {updates}")
                return True
            else:
                print(f"⚠️ [DMS ADAPTER] Customer {customer_id} not found in {self.file_path}")
                return False
        except Exception as e:
            print(f"[DMS ADAPTER ERROR] Failed to write customer file: {e}")
            return False


class ProductionRESTDMSAdapter(BaseDMSAdapter):
    """
    Production-grade REST DMS Adapter (Gap 2 Fix).
    Communicates with a live REST DMS API using HTTP.
    Extensible, highly configurable, and plug-and-play.
    """
    
    def __init__(self, api_url=None, api_key=None):
        self.api_url = api_url or os.getenv("DMS_API_URL", "https://api.alcon-dms.com/v1")
        self.api_key = api_key or os.getenv("DMS_API_KEY", "prod_dms_sec_key_xyz123")
        self.timeout = int(os.getenv("DMS_API_TIMEOUT", "5"))

    def fetch_customers(self):
        """Fetch all customer records from live REST DMS endpoint."""
        import requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        url = f"{self.api_url}/customers"
        try:
            print(f"[PROD DMS REST] Fetching customers from: {url}")
            response = requests.get(url, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[PROD DMS REST ERROR] Failed with status {response.status_code}: {response.text}")
                return []
        except Exception as e:
            print(f"[PROD DMS REST EXCEPTION] Error connecting to DMS REST API: {e}")
            return []

    def update_customer_state(self, customer_id: str, updates: dict) -> bool:
        """Sync back campaign triggers and final conversational outcomes to REST DMS."""
        import requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        url = f"{self.api_url}/customers/{customer_id}/state"
        try:
            print(f"[PROD DMS REST] Syncing back updates to customer {customer_id} at {url}")
            response = requests.patch(url, json=updates, headers=headers, timeout=self.timeout)
            if response.status_code in [200, 201, 204]:
                print(f"✅ [PROD DMS REST] Successfully updated customer {customer_id} in REST DMS")
                return True
            else:
                print(f"[PROD DMS REST ERROR] Update failed with status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"[PROD DMS REST EXCEPTION] Error updating customer in DMS REST API: {e}")
            return False
