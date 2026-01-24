import azure.functions as func
import json
import logging
import os
from src.state import session_store
from src.agent import agent
from src.acs import acs_handler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="acs/events", methods=["POST"])
async def acs_events(req: func.HttpRequest) -> func.HttpResponse:
    """Handle ACS EventGrid events."""
    try:
        events = req.get_json()
        for event in events:
            # EventGrid validation
            if event.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
                validation_code = event["data"]["validationCode"]
                return func.HttpResponse(json.dumps({"validationResponse": validation_code}), status_code=200)

            # Call Automation events (EventGrid format)
            event_type = event.get("eventType", "")
            data = event.get("data", {})
            call_connection_id = data.get("callConnectionId")
            
            if not call_connection_id:
                continue

            if "CallConnected" in event_type:
                logger.info(f"Call connected: {call_connection_id}")
                session = session_store.get_or_create_session(call_connection_id)
                # The participant ID is usually in the 'from' or 'to' field depending on the event
                # For CallConnected, it's often in 'participantId' or we can get it from the session later
                # We'll use a placeholder or try to find it in the data
                user_id = data.get("participantId") or "unknown"
                
                greeting = "Καλησπέρα σας! Είμαι η ψηφιακή εξυπηρέτηση του καταστήματος RetailCare. Πώς μπορώ να σας βοηθήσω;"
                await acs_handler.play_and_recognize(call_connection_id, greeting, user_id)
                
            elif "RecognizeCompleted" in event_type:
                logger.info(f"Speech recognized for call: {call_connection_id}")
                # Recognition data is in 'recognitionData'
                recognition_data = data.get("recognitionData", {})
                transcript = recognition_data.get("speechResult", {}).get("transcript", "")
                
                session = session_store.get_or_create_session(call_connection_id)
                response = await agent.process_utterance(session, transcript)
                
                user_id = data.get("participantId") or "unknown"
                await acs_handler.play_and_recognize(call_connection_id, response.response_text, user_id)

            elif "CallDisconnected" in event_type:
                logger.info(f"Call disconnected: {call_connection_id}")
                session_store.delete_session(call_connection_id)

        return func.HttpResponse(status_code=200)
    except Exception as e:
        logger.error(f"Error processing ACS event: {e}")
        return func.HttpResponse(status_code=500)

@app.route(route="dev/simulate", methods=["POST"])
async def simulate_call(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simulate a call for local testing.
    Payload: {"text": "...", "session_id": "optional-id", "phone": "optional-phone"}
    """
    try:
        body = req.get_json()
        text = body.get("text")
        session_id = body.get("session_id", "simulated-call-123")
        phone = body.get("phone", "306912345678")

        if not text:
            return func.HttpResponse("Missing 'text' in body", status_code=400)

        session = session_store.get_or_create_session(session_id, phone_number=phone)
        response = await agent.process_utterance(session, text)

        result = {
            "session_id": session_id,
            "user_input": text,
            "agent_intent": response.intent,
            "agent_response": response.response_text,
            "ticket_id": session.ticket_id,
            "ticket_url": session.ticket_url,
            "history_length": len(session.conversation_history)
        }

        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error in simulation: {e}")
        return func.HttpResponse(str(e), status_code=500)

@app.route(route="health", methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("Healthy", status_code=200)
