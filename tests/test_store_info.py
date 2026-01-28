"""
Unit tests for store information functionality
"""
import pytest
from datetime import datetime
from src.store_info import StoreInfo, store_info
import pytz


class TestStoreInfo:
    """Test store hours and information"""
    
    @pytest.fixture
    def store(self):
        """Create store info instance"""
        return StoreInfo()
    
    def test_get_store_hours_all(self, store):
        """Test getting all store hours"""
        hours = store.get_store_hours()
        assert "mon_fri" in hours or "sat" in hours or "sun" in hours
    
    def test_get_store_hours_saturday(self, store):
        """Test getting Saturday hours"""
        hours = store.get_store_hours("saturday")
        assert "sat" in hours or "10:00" in str(hours.values())
    
    def test_get_store_hours_sunday(self, store):
        """Test getting Sunday hours"""
        hours = store.get_store_hours("sunday")
        assert "sun" in hours or "Κλειστά" in str(hours.values())
    
    def test_render_hours_human_today(self, store):
        """Test rendering hours for today"""
        result = store.render_hours_human()
        assert "ανοιχτά" in result.lower() or "κλειστά" in result.lower()
        assert "Δευτέρα" in result or "Σάββατο" in result or "Κυριακή" in result
    
    def test_render_hours_human_saturday(self, store):
        """Test rendering hours for Saturday"""
        result = store.render_hours_human(day="saturday")
        assert "Σάββατο" in result
        assert "10:00" in result or "18:00" in result
    
    def test_get_current_day_name_el(self, store):
        """Test getting current day name in Greek"""
        day_name = store.get_current_day_name_el()
        assert day_name in ["Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο", "Κυριακή"]
    
    def test_get_today_hours(self, store):
        """Test getting today's hours"""
        hours = store.get_today_hours()
        assert hours is not None
        assert isinstance(hours, str)
    
    def test_get_location(self, store):
        """Test getting store location"""
        location = store.get_location()
        assert "Αθήνα" in location or len(location) > 0
    
    def test_get_contact_info(self, store):
        """Test getting contact information"""
        contact = store.get_contact_info()
        assert "phone" in contact
        assert "email" in contact
        assert "location" in contact
