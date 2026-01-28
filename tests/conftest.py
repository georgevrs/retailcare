"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import sys
from pathlib import Path

# Add project root to path so we can import src modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment variables
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
os.environ.setdefault("AZURE_OPENAI_KEY", "test-key")
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
os.environ.setdefault("ACS_CONNECTION_STRING", "endpoint=https://test.communication.azure.com/;accesskey=test")
os.environ.setdefault("SPEECH_KEY", "test-speech-key")
os.environ.setdefault("SPEECH_REGION", "westeurope")
os.environ.setdefault("GITHUB_OWNER", "test-owner")
os.environ.setdefault("GITHUB_REPO", "test-repo")
os.environ.setdefault("GITHUB_TOKEN", "test-token")

@pytest.fixture(scope="session")
def test_data_dir():
    """Get test data directory"""
    return Path(__file__).parent.parent / "data"

@pytest.fixture(scope="session")
def test_sessions_dir(tmp_path_factory):
    """Get temporary sessions directory"""
    return tmp_path_factory.mktemp("sessions")

@pytest.fixture(scope="session")
def base_url():
    """Base URL for deployed function app (for test_deployed.py)"""
    import os
    return os.getenv("FUNCTION_APP_URL", "http://localhost:7071")
