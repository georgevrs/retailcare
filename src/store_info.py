import json
import os
import logging
from datetime import datetime
from typing import Dict, Optional
import pytz

logger = logging.getLogger(__name__)

class StoreInfo:
    def __init__(self, file_path: str = "data/store_info.json"):
        self.file_path = file_path
        self.data = self._load_data()
        self.timezone = pytz.timezone(self.data.get("timezone", "Europe/Athens"))

    def _load_data(self) -> Dict:
        """Load store information from JSON file"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.warning(f"Store info file not found at {self.file_path}")
                return {
                    "hours": {
                        "mon_fri": "09:00-21:00",
                        "sat": "10:00-18:00",
                        "sun": "Κλειστά"
                    },
                    "timezone": "Europe/Athens"
                }
        except Exception as e:
            logger.error(f"Error loading store info: {e}")
            return {}

    def get_store_hours(self, day: Optional[str] = None) -> Dict[str, str]:
        """Get store hours for a specific day or all days"""
        hours = self.data.get("hours", {})
        if day:
            day_lower = day.lower()
            if day_lower in ["monday", "tuesday", "wednesday", "thursday", "friday", "δευτέρα", "τρίτη", "τετάρτη", "πέμπτη", "παρασκευή"]:
                return {"mon_fri": hours.get("mon_fri", "09:00-21:00")}
            elif day_lower in ["saturday", "saturday", "σάββατο"]:
                return {"sat": hours.get("sat", "10:00-18:00")}
            elif day_lower in ["sunday", "sunday", "κυριακή"]:
                return {"sun": hours.get("sun", "Κλειστά")}
        return hours

    def get_current_day_name_el(self) -> str:
        """Get current day name in Greek"""
        now = datetime.now(self.timezone)
        day_names = {
            0: "Κυριακή",
            1: "Δευτέρα",
            2: "Τρίτη",
            3: "Τετάρτη",
            4: "Πέμπτη",
            5: "Παρασκευή",
            6: "Σάββατο"
        }
        return day_names[now.weekday()]

    def get_today_hours(self) -> str:
        """Get today's hours"""
        now = datetime.now(self.timezone)
        weekday = now.weekday()
        
        hours = self.data.get("hours", {})
        if weekday < 5:  # Monday-Friday
            return hours.get("mon_fri", "09:00-21:00")
        elif weekday == 5:  # Saturday
            return hours.get("sat", "10:00-18:00")
        else:  # Sunday
            return hours.get("sun", "Κλειστά")

    def render_hours_human(self, day: Optional[str] = None, language: str = "el") -> str:
        """Render store hours in natural Greek language"""
        if language != "el":
            # For now, only support Greek
            language = "el"
        
        if day:
            # Specific day requested
            day_lower = day.lower()
            hours = self.get_store_hours(day)
            
            if "mon_fri" in hours:
                return f"Δευτέρα–Παρασκευή λειτουργούμε **{hours['mon_fri']}**."
            elif "sat" in hours:
                return f"Το Σάββατο λειτουργούμε **{hours['sat']}**."
            elif "sun" in hours:
                return f"Την Κυριακή είμαστε **{hours['sun']}**."
        
        # No specific day - show today or all hours
        now = datetime.now(self.timezone)
        weekday = now.weekday()
        day_name = self.get_current_day_name_el()
        today_hours = self.get_today_hours()
        
        all_hours = self.data.get("hours", {})
        
        if today_hours == "Κλειστά":
            response = f"Σήμερα ({day_name}) είμαστε **κλειστά**."
        else:
            response = f"Σήμερα ({day_name}) είμαστε ανοιχτά **{today_hours}**."
        
        # Add full schedule
        response += " Το ωράριο μας είναι: "
        response += f"Δευτέρα–Παρασκευή **{all_hours.get('mon_fri', '09:00-21:00')}**, "
        response += f"Σάββατο **{all_hours.get('sat', '10:00-18:00')}**, "
        response += f"Κυριακή **{all_hours.get('sun', 'Κλειστά')}**."
        
        return response

    def get_location(self) -> str:
        """Get store location"""
        return self.data.get("location", "Λεωφόρος Κηφισίας 100, Αθήνα")

    def get_contact_info(self) -> Dict[str, str]:
        """Get contact information"""
        return {
            "phone": self.data.get("phone", "210-1234567"),
            "email": self.data.get("email", "info@retailcare.gr"),
            "location": self.get_location()
        }

# Singleton instance
store_info = StoreInfo()
