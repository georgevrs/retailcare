import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Import our agent and models
# Note: We import inside the test or ensure path is correct
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.agent import agent
from src.state import session_store
from src.models import Intent

async def run_brain_test(test_name, user_input, expected_intent=None):
    print(f"\n--- TEST: {test_name} ---")
    print(f"User Said: '{user_input}'")
    
    # Create a fresh session for each test
    session_id = f"test-{test_name.lower().replace(' ', '-')}"
    session = session_store.get_or_create_session(session_id, phone_number="+306900000000")
    
    try:
        # Process through the AI Agent (The Brain)
        response = await agent.process_utterance(session, user_input)
        
        print(f"Detected Intent: {response.intent}")
        print(f"AI Response (Greek): {response.response_text}")
        
        if response.intent == Intent.COMPLAINT_TICKET:
            if session.ticket_id:
                print(f"✅ ACTION PERFORMED: Ticket #{session.ticket_id} created in GitHub.")
                print(f"Ticket URL: {session.ticket_url}")
            else:
                print("⚠️ INFO: Intent was COMPLAINT, but no ticket created yet (might need more info).")
        
        if expected_intent and response.intent != expected_intent:
            print(f"❌ MISMATCH: Expected {expected_intent}, got {response.intent}")
        else:
            print(f"✅ SUCCESS: {test_name} passed brain validation.")

    except Exception as e:
        print(f"❌ ERROR in {test_name}: {e}")

async def main():
    print("==================================================")
    print("RETAILCARE BRAIN TEST (STEP 2: AGENTIC LOGIC)")
    print("==================================================")
    print("Testing semantic understanding, intent routing, and tool use.")
    
    # 1. Test Information Routing (FAQ)
    await run_brain_test(
        "FAQ Routing (Hours)", 
        "Τι ώρα κλείνετε το Σάββατο;", 
        expected_intent=Intent.INFORMATION
    )

    # 2. Test FAQ with variations
    await run_brain_test(
        "FAQ Routing (Returns)", 
        "Πόσες μέρες έχω για να επιστρέψω κάτι που αγόρασα;", 
        expected_intent=Intent.INFORMATION
    )

    # 3. Test Complaint Routing & Agentic Action (Real GitHub Creation)
    # We provide enough info in one go to trigger immediate ticket creation
    await run_brain_test(
        "Agentic Action (Complaint)", 
        "Γεια σας, η παραγγελία μου #998877 έχει καθυστερήσει μια εβδομάδα και είμαι πολύ δυσαρεστημένος.", 
        expected_intent=Intent.COMPLAINT_TICKET
    )

    # 4. Test Ambiguity / Clarification
    await run_brain_test(
        "Clarification needed", 
        "Έχω ένα πρόβλημα.", 
        expected_intent=Intent.COMPLAINT_TICKET # Agent should ask for details
    )

    # 5. Test Polite Greeting
    await run_brain_test(
        "Greeting", 
        "Καλημέρα, πώς είστε;", 
        expected_intent=Intent.UNKNOWN # Or GREETING if implemented
    )

    print("\n==================================================")
    print("BRAIN TEST COMPLETE")
    print("Check your GitHub Issues to verify the real ticket creation.")

if __name__ == "__main__":
    asyncio.run(main())
