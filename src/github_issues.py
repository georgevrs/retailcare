import os
import httpx
import logging
from typing import Dict, Any, Optional, List
from src.models import TicketDetails

logger = logging.getLogger(__name__)

class GitHubTicketing:
    def __init__(self):
        self.owner = os.getenv("GITHUB_OWNER")
        self.repo = os.getenv("GITHUB_REPO")
        self.token = os.getenv("GITHUB_TOKEN")
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/issues"
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def create_ticket(self, details: TicketDetails, caller_phone: str, 
                           captured_summary: Optional[str] = None,
                           missing_info: Optional[List[str]] = None,
                           requested_resolution: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not all([self.owner, self.repo, self.token]):
            logger.error("GitHub credentials not configured")
            return None

        title = f"[Call Center] {details.category.value.capitalize()} - {details.title}"
        
        missing_info_section = ""
        if missing_info:
            missing_info_section = f"\n## Missing Information\n" + "\n".join(f"- {item}" for item in missing_info)
        
        requested_resolution_section = ""
        if requested_resolution:
            requested_resolution_section = f"\n## Customer's Requested Resolution\n{requested_resolution}"
        
        captured_summary_section = ""
        if captured_summary:
            captured_summary_section = f"\n## Captured Summary\n{captured_summary}"
        
        body = f"""
## Ticket Details
- **Caller Phone:** {caller_phone}
- **Category:** {details.category.value}
- **Urgency:** {details.urgency.value}
- **Order ID:** {details.order_id or 'N/A'}
- **Product:** {details.product or 'N/A'}
- **Store:** {details.store or 'N/A'}

{captured_summary_section}

## Summary
{details.description}
{requested_resolution_section}
{missing_info_section}

## Next Steps
- Review customer request
- Contact customer if additional information is needed
- Process according to category and urgency

---
*Created by RetailCare AI Call Center*
"""
        
        labels = [details.category.value, f"urgency:{details.urgency.value}", "channel:phone"]
        # Add extra labels if provided
        if details.extra_labels:
            labels.extend(details.extra_labels)
        
        payload = {
            "title": title,
            "body": body,
            "labels": labels
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Created GitHub ticket #{data['number']} at {data['html_url']}")
                return {
                    "number": str(data["number"]),
                    "url": data["html_url"]
                }
        except Exception as e:
            logger.error(f"Failed to create GitHub ticket: {str(e)}")
            return None

    async def post_comment(self, issue_number: int, comment: str) -> bool:
        """Post a comment to a GitHub issue"""
        if not all([self.owner, self.repo, self.token]):
            logger.error("GitHub credentials not configured")
            return False
        
        url = f"{self.base_url}/{issue_number}/comments"
        payload = {"body": comment}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                logger.info(f"Posted comment to issue #{issue_number}")
                return True
        except Exception as e:
            logger.error(f"Failed to post comment to issue #{issue_number}: {str(e)}")
            return False

    async def close_issue(self, issue_number: int) -> bool:
        """Close a GitHub issue"""
        if not all([self.owner, self.repo, self.token]):
            logger.error("GitHub credentials not configured")
            return False
        
        url = f"{self.base_url}/{issue_number}"
        payload = {"state": "closed"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(url, headers=self.headers, json=payload)
                response.raise_for_status()
                logger.info(f"Closed issue #{issue_number}")
                return True
        except Exception as e:
            logger.error(f"Failed to close issue #{issue_number}: {str(e)}")
            return False

# Singleton instance
github_client = GitHubTicketing()
