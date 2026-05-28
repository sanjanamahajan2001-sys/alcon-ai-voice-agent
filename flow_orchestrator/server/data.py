import json
import os

class MockCRM:
    def __init__(self):
        self.default = {"name": "Valued Customer", "tier": "generic", "exists": False}

    def __getitem__(self, key):
        if key == "default":
            return self.default
        return self.get(key)

    def get(self, phone, default=None):
        # Correct path: /home/sanjana/Alcon/poc/backend/data/customers.json
        # from server/ to poc/ is: ../../
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend/data/customers.json"))
        
        try:
            if not os.path.exists(path):
                print(f"DEBUG: customers.json not found at {path}")
                return default or self.default

            with open(path, "r") as f:
                customers = json.load(f)
                for c in customers:
                    if str(c.get("phone")) == str(phone):
                        # Enrich with fields needed for the flow logic
                        c["exists"] = True
                        # Infer 'tier' based on insurance status for the demo
                        c["tier"] = "premium" if c.get("insurance_provider") else "generic"
                        return c
        except Exception as e:
            print(f"DEBUG: Error reading CRM data: {e}")
            
        return default or self.default

MOCK_CRM = MockCRM()
