import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Find .env in the parent directory (root)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

def test_github_issue_creation():
    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")
    token = os.getenv("GITHUB_TOKEN")

    if not all([owner, repo, token]):
        print("Error: GITHUB_OWNER, GITHUB_REPO, or GITHUB_TOKEN not found in .env")
        return

    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "title": "[Call Center] delivery - Demo ticket",
        "body": "Caller: +30XXXXXXXXXX\n\nSummary: Demo\n\nDetails: Αυτό είναι ένα δοκιμαστικό ticket.",
        "labels": ["delivery", "urgency:low", "channel:phone"],
    }

    print(f"Testing GitHub issue creation for {owner}/{repo}...")
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Status Code: {r.status_code}")
        if r.status_code == 201:
            print("Successfully created demo ticket!")
            print(f"Ticket URL: {r.json().get('html_url')}")
        else:
            print(f"Failed to create ticket: {r.text}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_github_issue_creation()
