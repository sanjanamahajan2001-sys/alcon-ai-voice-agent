import json
import csv
import os
from datetime import datetime

class SAPBridge:
    def __init__(self, export_dir="data/sap_exports"):
        self.export_dir = export_dir
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)

    def generate_service_invoice_mock(self, customer, booking_details):
        """
        Simulates generating an SAP-compatible Invoice/Work Order
        """
        invoice_id = f"SAP-INV-{datetime.now().strftime('%y%m%d%H%M%S')}"
        
        # Structure data as a mock SAP IDoc (Intermediate Document)
        sap_data = {
            "IDOC_HEADER": {
                "DOC_NUM": invoice_id,
                "DOC_TYPE": "INVOIC02",
                "SENDER": "ALCON_AI_VOICE",
                "RECEIVER": "SAP_ERP_PROD"
            },
            "IDOC_DATA": {
                "CUSTOMER_NAME": customer['name'],
                "VEHICLE_MODEL": customer['car_model'],
                "SERVICE_DATE": booking_details.get('date'),
                "MILEAGE": booking_details.get('mileage'),
                "CONCERNS": booking_details.get('concerns'),
                "ESTIMATED_BASE_PRICE": "₹4,500.00",
                "CURRENCY": "INR"
            }
        }

        # Save as JSON (API Simulation)
        json_path = os.path.join(self.export_dir, f"{invoice_id}.json")
        with open(json_path, "w") as f:
            json.dump(sap_data, f, indent=4)

        # Save as CSV (Bulk Import Simulation)
        csv_path = os.path.join(self.export_dir, "daily_service_sync.csv")
        file_exists = os.path.exists(csv_path)
        
        with open(csv_path, "a", newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["InvoiceID", "Customer", "Model", "Date", "Mileage", "Price"])
            writer.writerow([
                invoice_id, 
                customer['name'], 
                customer['car_model'], 
                booking_details.get('date'), 
                booking_details.get('mileage'),
                "4500"
            ])

        print(f"[SAP BRIDGE] Successfully exported Invoice {invoice_id} to {self.export_dir}")
        return invoice_id

    def generate_lead_record(self, lead_details):
        """
        Simulates creating a Customer/Lead record in SAP CRM
        """
        lead_id = f"SAP-LEAD-{datetime.now().strftime('%y%m%d%H%M%S')}"
        path = os.path.join(self.export_dir, f"{lead_id}.json")
        
        with open(path, "w") as f:
            json.dump(lead_details, f, indent=4)
            
        print(f"[SAP BRIDGE] Lead {lead_details['name']} synced to SAP CRM.")
        return lead_id
