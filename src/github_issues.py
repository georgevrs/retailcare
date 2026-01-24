import os
import httpx
import logging
from typing import Dict, Any, Optional
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

    async def create_ticket(self, details: TicketDetails, caller_phone: str) -> Optional[Dict[str, Any]]:
        if not all([self.owner, self.repo, self.token]):
            logger.error("GitHub credentials not configured")
            return None

        title = f"[Call Center] {details.category.value.capitalize()} - {details.title}"
        
        body = f"""
## Ticket Details
- **Caller Phone:** {caller_phone}
- **Category:** {details.category.value}
- **Urgency:** {details.urgency.value}
- **Order ID:** {details.order_id or 'N/A'}
- **Product:** {details.product or 'N/A'}
- **Store:** {details.store or 'N/A'}

## Summary
{details.description}

---
*Created by RetailCare AI Call Center*
"""
        
        labels = [details.category.value, f"urgency:{details.urgency.value}", "channel:phone"]
        
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

# Singleton instance
github_client = GitHubTicketing()
