from datetime import datetime, date
import json

class TriggerEngine:
    """
    Configuration-driven business rules engine for Alcon Campaigns.
    Contains evaluation logic to qualify customers into 9 distinct campaigns
    relative to a standard demo reference date (May 21, 2026).
    """
    
    def __init__(self, reference_date_str="2026-05-21"):
        self.ref_date = datetime.strptime(reference_date_str, "%Y-%m-%d").date()
        print(f"🎯 [TRIGGER ENGINE] Configured with Reference Date: {self.ref_date}")

    def calculate_months_delta(self, last_service_date_str):
        try:
            last_date = datetime.strptime(last_service_date_str, "%Y-%m-%d").date()
            # Calculate total months difference
            return (self.ref_date.year - last_date.year) * 12 + (self.ref_date.month - last_date.month)
        except Exception:
            return 0

    def calculate_days_delta(self, target_date_str):
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            return (target_date - self.ref_date).days
        except Exception:
            return None

    def calculate_vehicle_age(self, reg_date_str):
        try:
            reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d").date()
            age_years = self.ref_date.year - reg_date.year
            # Adjust if birthday hasn't happened yet in the current year
            if (self.ref_date.month, self.ref_date.day) < (reg_date.month, reg_date.day):
                age_years -= 1
            return max(0, age_years)
        except Exception:
            return 0

    def evaluate_customer_eligibility(self, customer):
        """
        Evaluate eligibility for a single customer against all 9 business flows.
        Returns a dict of matching flow types and their metadata context.
        """
        eligible_flows = {}
        
        # Guard: DND customer bypass
        if customer.get("dnd_status", False):
            return eligible_flows

        # --- Rule 1: Service Booking Reminder (`booking`) ---
        # Service due date is soon (next 2 days) or already due based on intervals
        service_due_date_str = customer.get("service_due_date")
        last_service_date_str = customer.get("last_service_date")
        service_due_months = customer.get("service_due_months", 6)
        
        is_booking_eligible = False
        if service_due_date_str:
            days_to_due = self.calculate_days_delta(service_due_date_str)
            # Service due in the next 2 days or past due
            if days_to_due is not None and -15 <= days_to_due <= 2:
                is_booking_eligible = True
        elif last_service_date_str:
            months_delta = self.calculate_months_delta(last_service_date_str)
            if months_delta >= service_due_months:
                is_booking_eligible = True

        if is_booking_eligible and customer.get("service_status") not in ["booked", "in-progress", "completed"]:
            eligible_flows["booking"] = {
                "reason": "Service is due or scheduled soon",
                "days_due": self.calculate_days_delta(service_due_date_str) if service_due_date_str else None
            }

        # --- Rule 2: Pickup Coordination (`pd_pickup_coordination`) ---
        # Customer has service booked and logistics coordination is pending
        if customer.get("service_status") == "booked" and customer.get("pickup_status") == "pending":
            eligible_flows["pd_pickup_coordination"] = {
                "reason": "Service is booked. Logistics driver assignment needed."
            }

        # --- Rule 3: Workshop Update (`pd_workshop_update`) ---
        # Customer vehicle is in workshop and diagnostics estimation is active
        if customer.get("service_status") == "in-progress" and customer.get("workshop_update_eligible", False):
            eligible_flows["pd_workshop_update"] = {
                "reason": f"Service in progress. Current stage: {customer.get('workshop_stage', 'Part Allocation')}"
            }

        # --- Rule 4: Ready for Delivery (`pd_ready`) ---
        # Customer service is completed and drop coordination is pending
        if customer.get("service_status") == "completed" and customer.get("ready_for_delivery", False):
            eligible_flows["pd_ready"] = {
                "reason": "Service completed. Delivery ready."
            }

        # --- Rule 5: Insurance Renewal Campaign (`insurance_start`) ---
        # Policy is pending, not renewed, and expiring in 30 days
        insurance_expiry = customer.get("insurance_expiry_date")
        policy_status = customer.get("policy_status", "PENDING")
        
        if insurance_expiry and policy_status == "PENDING":
            days_to_expiry = self.calculate_days_delta(insurance_expiry)
            if days_to_expiry is not None and -3 <= days_to_expiry <= 30:
                # Stage 1: Initial (T-30 to T-16)
                if 16 <= days_to_expiry <= 30: stage = 1
                # Stage 2: Follow-up (T-15 to T-8)
                elif 8 <= days_to_expiry <= 15: stage = 2
                # Stage 3: Final Reminder (T-7 to T-4)
                elif 4 <= days_to_expiry <= 7: stage = 3
                # Stage 4: Urgent (T-3 to T-0)
                elif 0 <= days_to_expiry <= 3: stage = 4
                # Stage 5: Expired (Expired -1 to -3)
                else: stage = 5
                
                eligible_flows["insurance_start"] = {
                    "reason": f"Insurance renewal stage {stage} (Expiry in {days_to_expiry} days)",
                    "stage": stage,
                    "days_to_expiry": days_to_expiry
                }

        # --- Rule 6: Post 3rd-Day Feedback (`feedback_3rd_day`) ---
        # Last service date completed exactly 3 days ago relative to reference date (2026-05-18)
        if customer.get("service_status") == "completed" and last_service_date_str == "2026-05-18":
            eligible_flows["feedback_3rd_day"] = {
                "reason": "Post 3rd-Day Satisfaction Callback."
            }

        # --- Rule 7: 15-Day Feedback (`feedback_15day_v2`) ---
        # Last service date completed exactly 15 days ago relative to reference date (2026-05-06)
        if customer.get("service_status") == "completed" and last_service_date_str == "2026-05-06":
            eligible_flows["feedback_15day_v2"] = {
                "reason": "15-Day vehicle performance audit callback."
            }

        # --- Rule 8: Pre-Sales Upgrade Campaigns (`pre_sales`) ---
        # Qualifies based on vehicle age in years from registration date
        reg_date_str = customer.get("registration_date")
        car_model = customer.get("car_model", "")
        
        # For pre-sales campaigns, typically we look for our brand vehicles that aren't currently in workshop
        if reg_date_str and "Hyundai" in car_model and customer.get("service_status") != "in-progress":
            age = self.calculate_vehicle_age(reg_date_str)
            if age >= 5:
                sub_campaign = "exchange"
                reason = f"Vehicle Age {age} Years - Exchange Offer"
            elif age >= 3:
                sub_campaign = "upgrade"
                reason = f"Vehicle Age {age} Years - Upgrade Offer"
            else:
                sub_campaign = "emi_benefit"
                reason = f"Newer Vehicle ({age}y) - EMI Benefit Offer"
                
            eligible_flows["pre_sales"] = {
                "reason": reason,
                "campaign_type": sub_campaign,
                "vehicle_age": age
            }

        # --- Rule 9: Inbound Call Queue (`reception`) ---
        # Simulates a customer with an active inbound request waiting
        if customer.get("inbound_pending", False):
            eligible_flows["reception"] = {
                "reason": "Inbound client call waiting in queue"
            }

        return eligible_flows

    def scan_all_customers(self, customer_list):
        """Scan full list and return structured mapping of flow_type to list of eligible customer profiles."""
        scan_results = {
            "booking": [],
            "pd_pickup_coordination": [],
            "pd_workshop_update": [],
            "pd_ready": [],
            "insurance_start": [],
            "feedback_3rd_day": [],
            "feedback_15day_v2": [],
            "pre_sales": [],
            "reception": []
        }
        
        for customer in customer_list:
            matches = self.evaluate_customer_eligibility(customer)
            for flow_type, ctx in matches.items():
                if flow_type in scan_results:
                    # Enrich customer record with matching context
                    customer_enriched = {**customer, "campaign_context": ctx}
                    scan_results[flow_type].append(customer_enriched)
                    
        return scan_results
