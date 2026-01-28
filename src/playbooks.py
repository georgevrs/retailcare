import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class PlaybookStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    DRY_RUN = "dry_run"

class PlaybookRegistry:
    """Registry of allowed automation playbooks (allowlist only)"""
    
    def __init__(self):
        self.playbooks = {
            "fill_table": self._fill_table,
            "rerun_job": self._rerun_job,
            "sync_faq": self._sync_faq
        }
    
    def execute(self, playbook_name: str, parameters: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """
        Execute a playbook
        
        Args:
            playbook_name: Name of the playbook to execute
            parameters: Parameters for the playbook
            dry_run: If True, only simulate execution
        
        Returns:
            {
                "status": PlaybookStatus,
                "logs_summary": str,
                "next_steps": str,
                "result": Any
            }
        """
        if playbook_name not in self.playbooks:
            return {
                "status": PlaybookStatus.FAILED,
                "logs_summary": f"Unknown playbook: {playbook_name}",
                "next_steps": "Check playbook name and try again",
                "result": None
            }
        
        if dry_run:
            logger.info(f"[DRY RUN] Would execute playbook: {playbook_name} with parameters: {parameters}")
            return {
                "status": PlaybookStatus.DRY_RUN,
                "logs_summary": f"Dry run: Would execute {playbook_name}",
                "next_steps": "Add 'approved' label to execute for real",
                "result": None
            }
        
        try:
            playbook_func = self.playbooks[playbook_name]
            result = playbook_func(parameters)
            return {
                "status": PlaybookStatus.SUCCESS,
                "logs_summary": result.get("summary", "Execution completed"),
                "next_steps": result.get("next_steps", "Review results"),
                "result": result.get("data")
            }
        except Exception as e:
            logger.error(f"Error executing playbook {playbook_name}: {e}")
            return {
                "status": PlaybookStatus.FAILED,
                "logs_summary": f"Error: {str(e)}",
                "next_steps": "Check logs and retry if needed",
                "result": None
            }
    
    def _fill_table(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Fill an empty table from a source"""
        table_name = parameters.get("table_name")
        source = parameters.get("source")
        
        if not table_name or not source:
            raise ValueError("table_name and source are required")
        
        # In a real implementation, this would:
        # 1. Connect to database
        # 2. Check if table is empty
        # 3. Load data from source
        # 4. Insert into table
        # 5. Return row count
        
        logger.info(f"Filling table {table_name} from source {source}")
        
        # Simulated execution
        rows_inserted = 12345  # Would be actual count
        
        return {
            "summary": f"Filled table {table_name} with {rows_inserted} rows from {source}",
            "next_steps": "Verify data integrity",
            "data": {"rows_inserted": rows_inserted, "table_name": table_name}
        }
    
    def _rerun_job(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Re-run a data processing job"""
        job_name = parameters.get("job_name")
        job_parameters = parameters.get("parameters", {})
        
        if not job_name:
            raise ValueError("job_name is required")
        
        # In a real implementation, this would:
        # 1. Find the job definition
        # 2. Execute with provided parameters
        # 3. Monitor execution
        # 4. Return status
        
        logger.info(f"Re-running job {job_name} with parameters {job_parameters}")
        
        # Simulated execution
        return {
            "summary": f"Job {job_name} completed successfully",
            "next_steps": "Check job output",
            "data": {"job_name": job_name, "status": "completed"}
        }
    
    def _sync_faq(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Sync FAQ from external source"""
        source_url = parameters.get("source_url", "default")
        
        # In a real implementation, this would:
        # 1. Fetch FAQ from source
        # 2. Parse and validate
        # 3. Update local FAQ file
        # 4. Return update count
        
        logger.info(f"Syncing FAQ from {source_url}")
        
        # Simulated execution
        items_updated = 12  # Would be actual count
        
        return {
            "summary": f"Synced {items_updated} FAQ items from {source_url}",
            "next_steps": "Review updated FAQ content",
            "data": {"items_updated": items_updated, "source_url": source_url}
        }

# Singleton instance
playbook_registry = PlaybookRegistry()
