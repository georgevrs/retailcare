import requests
import json
import uuid
import sys
from pathlib import Path

# Add root to sys path to maybe use some models if needed
sys.path.append(str(Path(__file__).parent.parent))

def run_test_suite(base_url):
    print(f"🚀 STARTING DEPLOYED RESOURCE TEST SUITE")
    print(f"Target URL: {base_url}")
    print("-" * 50)

    # 1. Health Check
    test_health(base_url)

    # 2. Event Grid Handshake Simulation
    test_eventgrid_handshake(base_url)

    # 3. Simulated Inbound Call (Event Grid -> Function)
    # Note: This will trigger a real call to ACS answer_call API if configured.
    # If the connection string is wrong, this should log a 500 or error in Function logs.
    test_inbound_call_payload(base_url)

    # 4. Simulated Callback (ACS -> Function)
    test_callback_payload(base_url)

    print("-" * 50)
    print(f"✅ TEST SUITE FINISHED")
    print(f"Please check the Azure Function 'Log Stream' or 'Monitor' tab to verify the internal execution.")

def test_health(base_url):
    print(f"[TEST 1] Health Check...")
    try:
        r = requests.get(f"{base_url}/api/health", timeout=10)
        if r.status_code == 200:
            print(f"  ✅ Success: {r.text}")
        else:
            print(f"  ❌ Failed: Status {r.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

def test_eventgrid_handshake(base_url):
    print(f"[TEST 2] Event Grid Handshake Simulation...")
    v_code = str(uuid.uuid4())
    payload = [{
        "id": "test-id",
        "topic": "/subscriptions/test/resourceGroups/test/providers/Microsoft.Communication/CommunicationServices/test",
        "subject": "",
        "data": {"validationCode": v_code},
        "eventType": "Microsoft.EventGrid.SubscriptionValidationEvent",
        "eventTime": "2024-01-24T12:00:00.000Z",
        "metadataVersion": "1",
        "dataVersion": "1"
    }]
    try:
        r = requests.post(f"{base_url}/api/acs/events", json=payload, timeout=10)
        if r.status_code == 200:
            resp_data = r.json()
            if resp_data.get("validationResponse") == v_code:
                print(f"  ✅ Success: Handshake returned correct code.")
            else:
                print(f"  ❌ Failed: Handshake returned wrong code {resp_data}")
        else:
            print(f"  ❌ Failed: Status {r.status_code} - {r.text}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

def test_inbound_call_payload(base_url):
    print(f"[TEST 3] Simulated Inbound Call Payload...")
    # This payload mimics what ACS sends to Event Grid
    payload = [{
        "id": "test-call-id",
        "topic": "/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Communication/CommunicationServices/xxx",
        "subject": "/calling/callConnections/test-conn",
        "data": {
            "incomingCallContext": "mock-context-123",
            "from": {"rawId": "306900000000"},
            "to": {"rawId": "302100000000"},
            "callConnectionId": "test-conn-id"
        },
        "eventType": "Microsoft.Communication.IncomingCall",
        "eventTime": "2024-01-24T12:00:00.000Z",
        "metadataVersion": "1",
        "dataVersion": "1"
    }]
    try:
        r = requests.post(f"{base_url}/api/acs/events", json=payload, timeout=10)
        # Note: If ACS is not configured, our code logs error but returns 200 to Event Grid
        # to avoid infinite retries.
        if r.status_code == 200:
            print(f"  ✅ Success: Endpoint accepted inbound payload. CHECK LOGS for 'Answer' attempt.")
        else:
            print(f"  ❌ Failed: Status {r.status_code} - {r.text}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

def test_callback_payload(base_url):
    print(f"[TEST 4] Simulated ACS Callback (CallConnected)...")
    payload = [{
        "type": "Microsoft.Communication.CallConnected",
        "data": {
            "callConnectionId": "test-callback-id-" + str(uuid.uuid4())[:8],
            "serverCallId": "test-server-id",
            "correlationId": "test-corr-id",
            "participantId": "user-123"
        }
    }]
    try:
        r = requests.post(f"{base_url}/api/acs/callback", json=payload, timeout=10)
        if r.status_code == 200:
            print(f"  ✅ Success: Callback accepted. CHECK LOGS for 'Greeting' playback attempt.")
        else:
            print(f"  ❌ Failed: Status {r.status_code} - {r.text}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    # You can pass the URL as an argument or edit it here
    target = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:7071"
    run_test_suite(target)
