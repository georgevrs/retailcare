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
    """Endpoint A: EventGrid events (Incoming Call, Validation)."""
    logger.info("--- [HEARTBEAT] acs/events triggered ---")
    try:
        raw_payload = req.get_body().decode('utf-8')
        if not raw_payload:
            logger.warning("Received empty payload.")
            return func.HttpResponse(status_code=200)
            
        logger.info(f"Payload size: {len(raw_payload)} bytes")
        
        events = json.loads(raw_payload)
        # Event Grid always sends a list
        if not isinstance(events, list):
            events = [events]

        for event in events:
            event_type = event.get("eventType")
            
            # 1. Handle SubscriptionValidationEvent
            if event_type == "Microsoft.EventGrid.SubscriptionValidationEvent":
                validation_code = event["data"]["validationCode"]
                logger.info(f"EventGrid validation handshake. Code: {validation_code}")
                return func.HttpResponse(json.dumps({"validationResponse": validation_code}), status_code=200)

            # 2. Handle Incoming Call
            if event_type == "Microsoft.Communication.IncomingCall":
                data = event.get("data", {})
                incoming_call_context = data.get("incomingCallContext")
                caller_id = data.get("from", {}).get("rawId", "unknown")
                
                logger.info(f"--- INCOMING CALL DETECTED ---")
                logger.info(f"From: {caller_id}")
                
                # Pre-create session to store the phone number
                # We don't have the callConnectionId yet, but we can use the context as a temporary key
                # or just wait for CallConnected to get the ID and link it then.
                # Actually, ACS IncomingCall event doesn't give us the CallConnectionId yet.
                # It's generated when we answer.
                
                # IMPORTANT: Automatically derive callback URL if not set or pointing to Azure while running locally
                callback_url = os.getenv("ACS_CALLBACK_URL")
                
                # Dynamic callback detection (ideal for ngrok/local dev)
                request_url = req.url
                if "/api/acs/events" in request_url:
                    derived_callback = request_url.replace("/api/acs/events", "/api/acs/callback")
                    # If local or placeholder, use the derived one
                    if not callback_url or "retailcare-callcenter-fn" in callback_url or "<your-ngrok" in callback_url:
                        callback_url = derived_callback
                        logger.info(f"Using dynamically derived callback URL: {callback_url}")
                
                if not callback_url:
                    logger.error("CRITICAL: ACS_CALLBACK_URL could not be determined.")
                    return func.HttpResponse("Callback URL not configured", status_code=500)

                logger.info(f"Answering call. Callback: {callback_url}")
                logger.info(f"Incoming Context: {incoming_call_context[:50]}...")
                
                result = await acs_handler.answer_call(incoming_call_context, callback_url)
                
                if result:
                    conn_id = result.call_connection_id
                    logger.info(f"✅ Answer request sent. Connection ID: {conn_id}")
                    # Initialize session with phone number
                    session = session_store.get_or_create_session(conn_id, phone_number=caller_id)
                    logger.info(f"📝 Session created for {conn_id} with phone: {caller_id}")
                else:
                    logger.error("❌ Failed to answer call.")

        return func.HttpResponse(status_code=200)
    except Exception as e:
        logger.error(f"Error in acs/events handler: {str(e)}", exc_info=True)
        return func.HttpResponse(status_code=500)

@app.route(route="acs/callback", methods=["POST"])
async def acs_callback(req: func.HttpRequest) -> func.HttpResponse:
    """Endpoint B: Call Automation callback events (CallConnected, RecognizeCompleted)."""
    try:
        raw_payload = req.get_body().decode('utf-8')
        logger.info(f"=== ACS CALLBACK RECEIVED === Length: {len(raw_payload)}")
        logger.info(f"ACS CALLBACK RAW: {raw_payload[:2000]}...")
        
        events = json.loads(raw_payload)
        logger.info(f"Parsed {len(events) if isinstance(events, list) else 1} event(s)")
        # Call Automation callback can be a single event or a list
        if not isinstance(events, list):
            events = [events]

        for event in events:
            # Robust event type extraction
            event_type = event.get("type") or event.get("eventType") or ""
            data = event.get("data", {})
            call_connection_id = data.get("callConnectionId")
            
            logger.info(f"Processing event type: '{event_type}' | CallConnectionId: {call_connection_id}")
            
            if not call_connection_id:
                logger.warning(f"Callback event without callConnectionId: {event_type}")
                continue

            if "CallConnected" in event_type:
                logger.info(f"--- CALL CONNECTED --- ID: {call_connection_id}")
                session = session_store.get_or_create_session(call_connection_id)
                
                # Check if we already triggered the greeting (prevent double-fire)
                if session.greeting_triggered:
                    logger.info("Greeting already triggered for this call. Skipping.")
                    return func.HttpResponse(status_code=200)

                # Robustly find the PHONE NUMBER participant (not the bot)
                user_id = session.phone_number # From session storage
                
                # If still unknown, look at the participants list for the phone number
                if user_id == "unknown":
                    participants = data.get("participants", [])
                    for p in participants:
                        pid = p.get("identifier", {}).get("rawId")
                        # Only select phone number participants (4:+...)
                        if pid and pid.startswith("4:"):
                            user_id = pid
                            break
                
                if user_id == "unknown" or not user_id.startswith("4:"):
                    logger.warning("Phone number participant not found at CallConnected. Will wait for ParticipantsUpdated.")
                    return func.HttpResponse(status_code=200)

                greeting = "Καλησπέρα σας! Είμαι η ψηφιακή εξυπηρέτηση του καταστήματος RetailCare. Πώς μπορώ να σας βοηθήσω;"
                logger.info(f"🎤 STARTING MEDIA LOOP. Target participant: {user_id}")
                
                session.greeting_triggered = True
                session_store.save_session(session) # PERSIST!
                
                await acs_handler.play_and_recognize(call_connection_id, greeting, user_id)
                
            elif "ParticipantsUpdated" in event_type:
                logger.info(f"--- PARTICIPANTS UPDATED --- ID: {call_connection_id}")
                session = session_store.get_or_create_session(call_connection_id)
                
                if session.greeting_triggered:
                    return func.HttpResponse(status_code=200)

                participants = data.get("participants", [])
                user_id = "unknown"
                # Find the phone number participant (4:+...)
                for p in participants:
                    pid = p.get("identifier", {}).get("rawId")
                    if pid and pid.startswith("4:"):
                        user_id = pid
                        break
                
                if user_id != "unknown":
                    logger.info(f"📞 Found phone participant via ParticipantsUpdated: {user_id}")
                    session.phone_number = user_id
                    session.greeting_triggered = True
                    session_store.save_session(session)
                    
                    greeting = "Καλησπέρα σας! Είμαι η ψηφιακή εξυπηρέτηση του καταστήματος RetailCare. Πώς μπορώ να σας βοηθήσω;"
                    await acs_handler.play_and_recognize(call_connection_id, greeting, user_id)

            elif "RecognizeCompleted" in event_type:
                logger.info(f"--- SPEECH RECOGNIZED --- ID: {call_connection_id}")
                session = session_store.get_or_create_session(call_connection_id)
                
                recognition_data = data.get("recognitionData", {})
                transcript = (
                    recognition_data.get("speechResult", {}).get("transcript") or 
                    recognition_data.get("result", {}).get("text") or 
                    data.get("recognitionData", {}).get("transcript") or
                    data.get("transcript") or
                    ""
                )
                
                logger.info(f"User transcript: '{transcript}'")
                
                if not transcript.strip():
                    return func.HttpResponse(status_code=200)

                response = await agent.process_utterance(session, transcript)
                session_store.save_session(session) # PERSIST HISTORY!
                
                user_id = data.get("participantId") or session.phone_number
                logger.info(f"AI response: '{response.response_text}'")
                await acs_handler.play_and_recognize(call_connection_id, response.response_text, user_id)

            elif "RecognizeFailed" in event_type:
                logger.warning(f"--- RECOGNITION FAILED --- ID: {call_connection_id}")
                # Try to restart recognition if it was just a timeout
                session = session_store.get_or_create_session(call_connection_id)
                user_id = data.get("participantId") or session.phone_number
                retry_msg = "Με συγχωρείτε, δεν σας άκουσα καλά. Μπορείτε να επαναλάβετε;"
                await acs_handler.play_and_recognize(call_connection_id, retry_msg, user_id)

            elif "CallDisconnected" in event_type:
                logger.info(f"--- CALL DISCONNECTED --- ID: {call_connection_id}")
                session_store.delete_session(call_connection_id)
            
            else:
                logger.info(f"Other callback event: {event_type}")

        return func.HttpResponse(status_code=200)
    except Exception as e:
        logger.error(f"Error in acs/callback: {str(e)}", exc_info=True)
        return func.HttpResponse(status_code=500)

@app.route(route="dev/simulate", methods=["POST"])
async def simulate_call(req: func.HttpRequest) -> func.HttpResponse:
    """Simulate a call for local testing."""
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

        return func.HttpResponse(json.dumps(result, ensure_ascii=False), mimetype="application/json", status_code=200)
    except Exception as e:
        logger.error(f"Error in simulation: {e}")
        return func.HttpResponse(str(e), status_code=500)

@app.route(route="health", methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("Healthy", status_code=200)
