import requests
import json

def test_simulation_endpoint():
    url = "http://localhost:7071/api/dev/simulate"
    
    # Test 1: Information Request
    print("Testing Simulation: Information Request...")
    payload_info = {
        "text": "Ποιο είναι το ωράριο του καταστήματος;",
        "session_id": "test-session-info"
    }
    
    try:
        r = requests.post(url, json=payload_info, timeout=30)
        print(f"Status: {r.status_code}")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Ensure the Azure Function is running locally (func start). Error: {e}")

    print("\n" + "="*50 + "\n")

    # Test 2: Complaint Request
    print("Testing Simulation: Complaint Request...")
    payload_complaint = {
        "text": "Η παραγγελία μου #12345 καθυστερεί πολύ.",
        "session_id": "test-session-complaint"
    }
    
    try:
        r = requests.post(url, json=payload_complaint, timeout=30)
        print(f"Status: {r.status_code}")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_simulation_endpoint()
