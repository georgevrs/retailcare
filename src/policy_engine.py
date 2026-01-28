import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PolicyEngine:
    def __init__(self, file_path: str = "data/policies_el.json"):
        self.file_path = file_path
        self.policies = self._load_policies()

    def _load_policies(self) -> Dict:
        """Load policies from JSON file"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.warning(f"Policies file not found at {self.file_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading policies: {e}")
            return {}

    def check_policy(self, policy_key: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if a request matches policy requirements
        
        Args:
            policy_key: e.g., "refund", "cancellation"
            slots: Dictionary with slot values (order_id, reason, days_since_delivery, etc.)
        
        Returns:
            {
                "eligible": bool,
                "what_we_need": List[str],
                "next_steps_text_el": str,
                "policy_details": Dict
            }
        """
        policy_section = self.policies.get(policy_key, {})
        
        if policy_key == "refund":
            return self._check_refund_policy(policy_section, slots)
        elif policy_key == "cancellation":
            return self._check_cancellation_policy(policy_section, slots)
        else:
            return {
                "eligible": True,
                "what_we_need": [],
                "next_steps_text_el": "Θα εξετάσουμε το αίτημά σας.",
                "policy_details": {}
            }

    def _check_refund_policy(self, policy_section: Dict, slots: Dict[str, Any]) -> Dict[str, Any]:
        """Check refund policy based on reason"""
        reason = slots.get("reason", "").lower()
        days_since_delivery = slots.get("days_since_delivery")
        condition = slots.get("condition", "").lower()
        
        # Map reason to policy
        reason_map = {
            "changed_mind": ["άλλαξα", "changed", "mind", "γνώμη"],
            "damaged": ["κατεστραμμένο", "damaged", "σπασμένο", "broken"],
            "wrong_item": ["λάθος", "wrong", "διαφορετικό", "different"],
            "defective": ["ελαττωματικό", "defective", "δεν λειτουργεί", "broken"]
        }
        
        matched_policy = None
        for policy_name, keywords in reason_map.items():
            if any(k in reason for k in keywords):
                matched_policy = policy_section.get(policy_name)
                break
        
        if not matched_policy:
            # Default policy
            matched_policy = policy_section.get("changed_mind", {})
        
        eligible_days = matched_policy.get("eligible_days", 14)
        required_condition = matched_policy.get("condition", "any")
        required_evidence = matched_policy.get("required_evidence", [])
        
        # Check eligibility
        eligible = True
        what_we_need = []
        issues = []
        
        # Check days since delivery
        if days_since_delivery is not None:
            if days_since_delivery > eligible_days:
                eligible = False
                issues.append(f"Η επιστροφή πρέπει να γίνει εντός {eligible_days} ημερών από την παράδοση.")
        else:
            what_we_need.append("Πόσες ημέρες έχουν περάσει από την παράδοση;")
        
        # Check condition
        if required_condition != "any":
            if not condition or required_condition not in condition:
                what_we_need.append(f"Το προϊόν πρέπει να είναι {required_condition}")
        
        # Check required evidence
        if required_evidence:
            for evidence_type in required_evidence:
                if evidence_type == "photo":
                    what_we_need.append("Φωτογραφία του προϊόντος")
                elif evidence_type == "description":
                    what_we_need.append("Περιγραφή του προβλήματος")
        
        # Generate next steps text
        if not eligible:
            next_steps = f"Δυστυχώς, το αίτημά σας δεν πληροί τις προϋποθέσεις επιστροφής. {' '.join(issues)}"
        elif what_we_need:
            next_steps = f"Για να προχωρήσουμε, χρειαζόμαστε: {', '.join(what_we_need)}."
        else:
            next_steps = "Το αίτημά σας πληροί τις προϋποθέσεις. Θα προχωρήσουμε με την επιστροφή."
        
        return {
            "eligible": eligible,
            "what_we_need": what_we_need,
            "next_steps_text_el": next_steps,
            "policy_details": matched_policy,
            "eligible_days": eligible_days
        }

    def _check_cancellation_policy(self, policy_section: Dict, slots: Dict[str, Any]) -> Dict[str, Any]:
        """Check cancellation policy based on shipment status"""
        shipment_status = slots.get("shipment_status", "").lower()
        
        if "shipped" in shipment_status or "αποστάληκε" in shipment_status:
            policy = policy_section.get("after_shipment", {})
            alternative = policy.get("alternative", "return_after_delivery")
            
            return {
                "eligible": False,
                "what_we_need": [],
                "next_steps_text_el": policy.get("description_el", "Η παραγγελία έχει ήδη αποσταλεί. Μπορείτε να την επιστρέψετε μετά την παράδοση."),
                "policy_details": policy,
                "alternative": alternative
            }
        else:
            policy = policy_section.get("before_shipment", {})
            return {
                "eligible": True,
                "what_we_need": [],
                "next_steps_text_el": "Η ακύρωση μπορεί να γίνει. Θα προχωρήσουμε αμέσως.",
                "policy_details": policy
            }

# Singleton instance
policy_engine = PolicyEngine()
