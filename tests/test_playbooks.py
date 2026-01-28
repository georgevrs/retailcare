"""
Unit tests for automation playbooks
"""
import pytest
from src.playbooks import PlaybookRegistry, PlaybookStatus, playbook_registry


class TestPlaybookRegistry:
    """Test playbook registry and execution"""
    
    @pytest.fixture
    def registry(self):
        """Create playbook registry"""
        return PlaybookRegistry()
    
    def test_execute_unknown_playbook(self, registry):
        """Test executing unknown playbook"""
        result = registry.execute("unknown_playbook", {}, dry_run=True)
        assert result["status"] == PlaybookStatus.FAILED
        assert "Unknown playbook" in result["logs_summary"]
    
    def test_execute_fill_table_dry_run(self, registry):
        """Test fill_table playbook in dry-run mode"""
        result = registry.execute(
            "fill_table",
            {"table_name": "orders", "source": "backup"},
            dry_run=True
        )
        assert result["status"] == PlaybookStatus.DRY_RUN
        assert "Would execute" in result["logs_summary"]
    
    def test_execute_fill_table_live(self, registry):
        """Test fill_table playbook in live mode"""
        result = registry.execute(
            "fill_table",
            {"table_name": "orders", "source": "backup"},
            dry_run=False
        )
        assert result["status"] == PlaybookStatus.SUCCESS
        assert "Filled table" in result["logs_summary"]
        assert "rows_inserted" in result["result"]
    
    def test_execute_fill_table_missing_params(self, registry):
        """Test fill_table with missing parameters"""
        result = registry.execute(
            "fill_table",
            {"table_name": "orders"},  # Missing source
            dry_run=False
        )
        assert result["status"] == PlaybookStatus.FAILED
    
    def test_execute_rerun_job(self, registry):
        """Test rerun_job playbook"""
        result = registry.execute(
            "rerun_job",
            {"job_name": "daily_ingestion", "parameters": {"start_date": "2026-01-01"}},
            dry_run=False
        )
        assert result["status"] == PlaybookStatus.SUCCESS
        assert "Job" in result["logs_summary"]
    
    def test_execute_sync_faq(self, registry):
        """Test sync_faq playbook"""
        result = registry.execute(
            "sync_faq",
            {"source_url": "https://example.com/faq.json"},
            dry_run=False
        )
        assert result["status"] == PlaybookStatus.SUCCESS
        assert "Synced" in result["logs_summary"]
