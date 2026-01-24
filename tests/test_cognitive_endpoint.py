"""
Test to validate Cognitive Services endpoint configuration for ACS Call Automation.

This test helps debug the "Request not allowed when Cognitive Service Configuration not set" error.
"""
import os
import sys
import logging
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.acs import ACSCallHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_endpoint_construction():
    """Test that cognitive services endpoint is constructed correctly."""
    
    test_cases = [
        {
            "name": "Multi-service Cognitive Services endpoint (preferred)",
            "env": {
                "AZURE_OPENAI_ENDPOINT": "https://georg-misszhma-centralus.cognitiveservices.azure.com/",
                "SPEECH_REGION": "francecentral"
            },
            "expected": "https://georg-misszhma-centralus.cognitiveservices.azure.com"
        },
        {
            "name": "Multi-service without trailing slash",
            "env": {
                "AZURE_OPENAI_ENDPOINT": "https://georg-misszhma-centralus.cognitiveservices.azure.com",
                "SPEECH_REGION": "francecentral"
            },
            "expected": "https://georg-misszhma-centralus.cognitiveservices.azure.com"
        },
        {
            "name": "Fallback to regional Speech endpoint",
            "env": {
                "SPEECH_REGION": "francecentral"
            },
            "expected": "https://francecentral.cognitiveservices.azure.com/"
        }
    ]
    
    handler = ACSCallHandler()
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {test_case['name']}")
        print(f"{'='*60}")
        
        # Set environment
        for key, value in test_case['env'].items():
            os.environ[key] = value
        
        # Clear any keys not in this test case
        if 'AZURE_OPENAI_ENDPOINT' not in test_case['env']:
            os.environ.pop('AZURE_OPENAI_ENDPOINT', None)
        
        # Simulate the endpoint construction logic from answer_call
        cognitive_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not cognitive_endpoint:
            speech_region = os.getenv("SPEECH_REGION", "francecentral")
            cognitive_endpoint = f"https://{speech_region}.cognitiveservices.azure.com/"
        else:
            cognitive_endpoint = cognitive_endpoint.rstrip("/")
        
        print(f"Environment: {test_case['env']}")
        print(f"Constructed: {cognitive_endpoint}")
        print(f"Expected:    {test_case['expected']}")
        
        assert cognitive_endpoint == test_case['expected'], \
            f"Endpoint mismatch! Got {cognitive_endpoint}, expected {test_case['expected']}"
        
        print(f"✅ PASS")
    
    print(f"\n{'='*60}")
    print("All endpoint construction tests passed!")
    print(f"{'='*60}\n")


def test_answer_call_with_mock():
    """Test that answer_call passes the correct endpoint to ACS SDK."""
    
    # Set up environment
    os.environ["ACS_CONNECTION_STRING"] = "endpoint=https://test.communication.azure.com/;accesskey=testkey123"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://georg-misszhma-centralus.cognitiveservices.azure.com/"
    os.environ["SPEECH_REGION"] = "francecentral"
    
    handler = ACSCallHandler()
    
    # Mock the CallAutomationClient
    with patch('src.acs.CallAutomationClient') as mock_client_class:
        # Create a mock client instance
        mock_client_instance = MagicMock()
        mock_client_class.from_connection_string.return_value = mock_client_instance
        
        # Create a mock answer result
        mock_answer_result = Mock()
        mock_answer_result.call_connection_id = "test-connection-id-123"
        mock_client_instance.answer_call.return_value = mock_answer_result
        
        # Force re-initialization
        handler._client = None
        
        # Call answer_call
        import asyncio
        result = asyncio.run(handler.answer_call(
            incoming_call_context="fake-context-token",
            callback_url="https://test.com/callback"
        ))
        
        # Verify answer_call was called with the correct endpoint
        mock_client_instance.answer_call.assert_called_once()
        call_args = mock_client_instance.answer_call.call_args
        
        print(f"\n{'='*60}")
        print("Answer Call Mock Test")
        print(f"{'='*60}")
        print(f"Called with args: {call_args[1]}")
        print(f"Cognitive endpoint: {call_args[1]['cognitive_services_endpoint']}")
        
        expected_endpoint = "https://georg-misszhma-centralus.cognitiveservices.azure.com"
        actual_endpoint = call_args[1]['cognitive_services_endpoint']
        
        assert actual_endpoint == expected_endpoint, \
            f"Wrong endpoint! Got {actual_endpoint}, expected {expected_endpoint}"
        
        print(f"✅ Correct endpoint passed to ACS SDK")
        print(f"{'='*60}\n")


def manual_test_instructions():
    """Print manual testing instructions."""
    print(f"\n{'='*60}")
    print("MANUAL TEST INSTRUCTIONS")
    print(f"{'='*60}")
    print("""
To test the actual ACS Call Automation setup:

1. Check your Azure Portal:
   - Go to your Cognitive Services resource: georg-misszhma-centralus
   - Verify it has Speech Services enabled
   - Note the endpoint URL

2. Verify environment variables in Azure Function App:
   az functionapp config appsettings list \\
     --name retailcare-callcenter-fn-g6e9e6a2grgberd2 \\
     --resource-group mlfunq7-a03b2-rg-francecentral \\
     --query "[?name=='AZURE_OPENAI_ENDPOINT'].{name:name, value:value}"

3. The endpoint should be:
   https://georg-misszhma-centralus.cognitiveservices.azure.com/
   
   NOT:
   - https://francecentral.api.cognitive.microsoft.com/
   - https://francecentral.cognitiveservices.azure.com/

4. If wrong, update it:
   az functionapp config appsettings set \\
     --name retailcare-callcenter-fn-g6e9e6a2grgberd2 \\
     --resource-group mlfunq7-a03b2-rg-francecentral \\
     --settings AZURE_OPENAI_ENDPOINT="https://georg-misszhma-centralus.cognitiveservices.azure.com/"

5. Test a call and check logs for:
   [Information]   Cognitive Endpoint: https://georg-misszhma-centralus.cognitiveservices.azure.com
""")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("COGNITIVE SERVICES ENDPOINT TEST SUITE")
    print("="*60 + "\n")
    
    try:
        test_endpoint_construction()
        test_answer_call_with_mock()
        manual_test_instructions()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
