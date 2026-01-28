import logging
import re
from typing import Dict, Any, Optional, List
from src.playbooks import playbook_registry, PlaybookStatus
from src.github_issues import github_client

logger = logging.getLogger(__name__)

class RemediationWorker:
    """Process GitHub tickets for automated remediation"""
    
    def __init__(self):
        self.required_labels = ["automation:run", "approved"]
        self.playbook_label_prefix = "playbook:"
    
    async def process_ticket_for_automation(self, issue_data: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """
        Process a GitHub issue for automated remediation
        
        Args:
            issue_data: GitHub issue data with labels, body, number
            dry_run: If True, only simulate execution
        
        Returns:
            {
                "processed": bool,
                "status": str,
                "message": str,
                "execution_result": Optional[Dict]
            }
        """
        issue_number = issue_data.get("number")
        labels = [label.get("name", label) if isinstance(label, dict) else label for label in issue_data.get("labels", [])]
        body = issue_data.get("body", "")
        
        logger.info(f"Processing issue #{issue_number} for automation (dry_run={dry_run})")
        
        # Safety gate 1: Check required labels
        if not self._has_required_labels(labels):
            missing = [l for l in self.required_labels if l not in labels]
            return {
                "processed": False,
                "status": "skipped",
                "message": f"Missing required labels: {', '.join(missing)}",
                "execution_result": None
            }
        
        # Safety gate 2: Find playbook
        playbook_name = self._extract_playbook_name(labels)
        if not playbook_name:
            return {
                "processed": False,
                "status": "skipped",
                "message": "No playbook label found (e.g., playbook:fill_table)",
                "execution_result": None
            }
        
        # Safety gate 3: Extract parameters from issue body
        parameters = self._extract_parameters(body, playbook_name)
        
        # Execute playbook
        execution_result = playbook_registry.execute(playbook_name, parameters, dry_run=dry_run)
        
        # Post comment back to issue
        comment = self._format_execution_comment(execution_result, dry_run)
        if issue_number:
            await github_client.post_comment(issue_number, comment)
        
        return {
            "processed": True,
            "status": execution_result["status"].value if hasattr(execution_result["status"], "value") else str(execution_result["status"]),
            "message": execution_result["logs_summary"],
            "execution_result": execution_result
        }
    
    def _has_required_labels(self, labels: List[str]) -> bool:
        """Check if issue has all required labels"""
        return all(req_label in labels for req_label in self.required_labels)
    
    def _extract_playbook_name(self, labels: List[str]) -> Optional[str]:
        """Extract playbook name from labels"""
        for label in labels:
            if isinstance(label, str) and label.startswith(self.playbook_label_prefix):
                return label[len(self.playbook_label_prefix):]
            elif isinstance(label, dict) and label.get("name", "").startswith(self.playbook_label_prefix):
                return label["name"][len(self.playbook_label_prefix):]
        return None
    
    def _extract_parameters(self, body: str, playbook_name: str) -> Dict[str, Any]:
        """Extract parameters from issue body"""
        parameters = {}
        
        # Try to parse structured format
        # Example: "Table X is empty; please refill from Source Y."
        if playbook_name == "fill_table":
            # Look for "table" and "source" keywords
            table_match = re.search(r'table\s+(\w+)', body, re.IGNORECASE)
            source_match = re.search(r'(?:from|source)\s+(\w+)', body, re.IGNORECASE)
            
            if table_match:
                parameters["table_name"] = table_match.group(1)
            if source_match:
                parameters["source"] = source_match.group(1)
        
        elif playbook_name == "rerun_job":
            # Try multiple patterns - order matters (more specific first)
            # Pattern 1: "re-run the daily_ingestion job" or "rerun job daily_ingestion"
            job_match = re.search(r'(?:re-run|rerun|run)\s+(?:the\s+)?(?:job\s+)?(\w+)(?:\s+job)?', body, re.IGNORECASE)
            if not job_match:
                # Pattern 2: "job daily_ingestion"
                job_match = re.search(r'job\s+(\w+)', body, re.IGNORECASE)
            if job_match:
                parameters["job_name"] = job_match.group(1)
        
        elif playbook_name == "sync_faq":
            url_match = re.search(r'url[:\s]+([^\s]+)', body, re.IGNORECASE)
            if url_match:
                parameters["source_url"] = url_match.group(1)
        
        # Fallback: try to extract from markdown code blocks
        if not parameters:
            code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', body, re.DOTALL)
            if code_block_match:
                try:
                    import json
                    parameters = json.loads(code_block_match.group(1))
                except:
                    pass
        
        return parameters
    
    def _format_execution_comment(self, execution_result: Dict[str, Any], dry_run: bool) -> str:
        """Format execution result as GitHub comment"""
        status = execution_result.get("status")
        logs = execution_result.get("logs_summary", "")
        next_steps = execution_result.get("next_steps", "")
        
        prefix = "🔍 **DRY RUN** - " if dry_run else "✅ **EXECUTED** - "
        
        comment = f"""{prefix}Automation Playbook Execution

**Status:** {status}

**Summary:**
{logs}

**Next Steps:**
{next_steps}

---
*Executed by RetailCare Remediation Worker*
"""
        return comment

# Singleton instance
remediation_worker = RemediationWorker()
