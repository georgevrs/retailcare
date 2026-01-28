"""
Unit tests for remediation worker
"""
import pytest
from unittest.mock import AsyncMock, patch
from src.remediation_worker import RemediationWorker, remediation_worker
from src.playbooks import PlaybookStatus


class TestRemediationWorker:
    """Test remediation worker functionality"""
    
    @pytest.fixture
    def worker(self):
        """Create remediation worker"""
        return RemediationWorker()
    
    def test_has_required_labels(self, worker):
        """Test checking for required labels"""
        labels = ["automation:run", "approved", "playbook:fill_table"]
        assert worker._has_required_labels(labels) is True
        
        labels_missing = ["automation:run", "playbook:fill_table"]  # Missing approved
        assert worker._has_required_labels(labels_missing) is False
    
    def test_extract_playbook_name(self, worker):
        """Test extracting playbook name from labels"""
        labels = ["automation:run", "approved", "playbook:fill_table"]
        assert worker._extract_playbook_name(labels) == "fill_table"
        
        labels_dict = [
            {"name": "automation:run"},
            {"name": "playbook:rerun_job"}
        ]
        assert worker._extract_playbook_name(labels_dict) == "rerun_job"
        
        labels_no_playbook = ["automation:run", "approved"]
        assert worker._extract_playbook_name(labels_no_playbook) is None
    
    def test_extract_parameters_fill_table(self, worker):
        """Test extracting parameters for fill_table"""
        body = "Table orders is empty; please refill from Source backup_db."
        params = worker._extract_parameters(body, "fill_table")
        
        assert "table_name" in params or "orders" in str(params.values())
    
    def test_extract_parameters_rerun_job(self, worker):
        """Test extracting parameters for rerun_job"""
        # Test with pattern that should match
        body = "Please re-run the daily_ingestion job."
        params = worker._extract_parameters(body, "rerun_job")
        
        # The updated regex should match "re-run the daily_ingestion job"
        assert "job_name" in params
        assert params["job_name"] == "daily_ingestion"
    
    def test_extract_parameters_json(self, worker):
        """Test extracting parameters from JSON code block"""
        body = """
        Please execute with:
        ```json
        {"table_name": "orders", "source": "backup"}
        ```
        """
        params = worker._extract_parameters(body, "fill_table")
        assert "table_name" in params or "orders" in str(params.values())
    
    @pytest.mark.asyncio
    async def test_process_ticket_missing_labels(self, worker):
        """Test processing ticket with missing required labels"""
        issue_data = {
            "number": 100,
            "labels": ["automation:run"],  # Missing approved
            "body": "Test"
        }
        
        result = await worker.process_ticket_for_automation(issue_data, dry_run=True)
        assert result["processed"] is False
        assert result["status"] == "skipped"
        assert "Missing required labels" in result["message"]
    
    @pytest.mark.asyncio
    async def test_process_ticket_no_playbook(self, worker):
        """Test processing ticket without playbook label"""
        issue_data = {
            "number": 100,
            "labels": ["automation:run", "approved"],
            "body": "Test"
        }
        
        result = await worker.process_ticket_for_automation(issue_data, dry_run=True)
        assert result["processed"] is False
        assert "No playbook label" in result["message"]
    
    @pytest.mark.asyncio
    async def test_process_ticket_success_dry_run(self, worker):
        """Test successful ticket processing in dry-run mode"""
        issue_data = {
            "number": 100,
            "labels": ["automation:run", "approved", "playbook:fill_table"],
            "body": "Table orders is empty; please refill from Source backup."
        }
        
        with patch("src.remediation_worker.github_client.post_comment", new_callable=AsyncMock):
            result = await worker.process_ticket_for_automation(issue_data, dry_run=True)
            assert result["processed"] is True
            assert result["status"] == "dry_run"
    
    def test_format_execution_comment(self, worker):
        """Test formatting execution comment"""
        execution_result = {
            "status": PlaybookStatus.SUCCESS,
            "logs_summary": "Filled table orders with 12345 rows",
            "next_steps": "Verify data integrity"
        }
        
        comment = worker._format_execution_comment(execution_result, dry_run=False)
        assert "EXECUTED" in comment
        assert "Filled table" in comment
        assert "12345" in comment
