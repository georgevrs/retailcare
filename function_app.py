import azure.functions as func
import json
import logging
import os
import asyncio

from src.state import session_store
from src.agent import agent
from src.acs import acs_handler
from src.call_state import call_state

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DIAGNOSTIC: Log critical environment variables at startup
logger.info("=" * 80)
logger.info("FUNCTION APP STARTUP - ENVIRONMENT CHECK")
logger.info("=" * 80)
logger.info(f"FUNCTIONS_WORKER_RUNTIME = {os.getenv('FUNCTIONS_WORKER_RUNTIME', '<NOT SET>')}")
logger.info(f"AzureWebJobsFeatureFlags = {os.getenv('AzureWebJobsFeatureFlags', '<NOT SET>')}")
logger.info(f"FUNCTIONS_EXTENSION_VERSION = {os.getenv('FUNCTIONS_EXTENSION_VERSION', '<NOT SET>')}")
logger.info(f"PYTHON_VERSION = {os.getenv('PYTHON_VERSION', '<NOT SET>')}")
logger.info(f"WEBSITE_SITE_NAME = {os.getenv('WEBSITE_SITE_NAME', '<NOT SET>')}")
logger.info(f"AzureWebJobsStorage = {'<SET>' if os.getenv('AzureWebJobsStorage') else '<NOT SET>'}")
logger.info("=" * 80)

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
                
                # Pre-create session to store the phone number if needed.
                # We do NOT start media here; CallConnected/ParticipantsUpdated will trigger greeting safely.
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
                    # Initialize session with phone number; greeting will be started on CallConnected/ParticipantsUpdated
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
                
                # Avoid double-greeting if we've already done it on this call
                if session.greeting_triggered:
                    logger.info("Greeting already triggered for this call (CallConnected). Skipping.")
                    return func.HttpResponse(status_code=200)

                # Try to get the phone participant from session or event participants
                user_id = session.phone_number
                if not user_id or user_id == "unknown":
                    participants = data.get("participants", [])
                    for p in participants:
                        pid = (p.get("identifier") or {}).get("rawId")
                        # Only select phone number participants (4:+...)
                        if isinstance(pid, str) and pid.startswith("4:"):
                            user_id = pid
                            break

                if not user_id or not isinstance(user_id, str) or not user_id.startswith("4:"):
                    logger.warning("Phone number participant not found at CallConnected. Will wait for ParticipantsUpdated.")
                    return func.HttpResponse(status_code=200)

                # Persist phone rawId in both session_store and durable call_state
                session.phone_number = user_id
                session.greeting_triggered = True
                session_store.save_session(session)
                call_state.put_phone(call_connection_id, user_id)

                greeting = "Καλησπέρα σας! Είμαι η ψηφιακή εξυπηρέτηση του καταστήματος RetailCare. Πώς μπορώ να σας βοηθήσω;"
                logger.info(f"🎤 STARTING MEDIA LOOP. Target participant: {user_id}")
                await acs_handler.play_and_recognize(call_connection_id, greeting, user_id)
                
            elif "ParticipantsUpdated" in event_type:
                logger.info(f"--- PARTICIPANTS UPDATED --- ID: {call_connection_id}")
                session = session_store.get_or_create_session(call_connection_id)
                
                # If we've already greeted, nothing to do here
                if session.greeting_triggered:
                    return func.HttpResponse(status_code=200)

                participants = data.get("participants", [])
                user_id = "unknown"
                # Find the phone number participant (4:+...)
                for p in participants:
                    pid = (p.get("identifier") or {}).get("rawId")
                    if isinstance(pid, str) and pid.startswith("4:"):
                        user_id = pid
                        break
                
                if user_id != "unknown":
                    logger.info(f"📞 Found phone participant via ParticipantsUpdated: {user_id}")
                    session.phone_number = user_id
                    session.greeting_triggered = True
                    session_store.save_session(session)
                    call_state.put_phone(call_connection_id, user_id)
                    
                    greeting = "Καλησπέρα σας! Είμαι η ψηφιακή εξυπηρέτηση του καταστήματος RetailCare. Πώς μπορώ να σας βοηθήσω;"
                    await acs_handler.play_and_recognize(call_connection_id, greeting, user_id)

            elif "RecognizeCompleted" in event_type:
                logger.info(f"--- SPEECH RECOGNIZED --- ID: {call_connection_id}")
                session = session_store.get_or_create_session(call_connection_id)
                
                # CRITICAL FIX: The SDK returns "speechResult.speech", NOT "transcript"
                speech_result = data.get("speechResult", {})
                transcript = speech_result.get("speech", "").strip()
                
                # Log raw data for debugging
                logger.info(f"Raw speechResult: {speech_result}")
                logger.info(f"Extracted transcript: '{transcript}'")
                
                if not transcript:
                    logger.warning("Empty transcript received, skipping agent processing")
                    return func.HttpResponse(status_code=200)

                response = await agent.process_utterance(session, transcript)
                session_store.save_session(session)
                
                # Determine the correct participant to respond to.
                user_id = data.get("participantId") or session.phone_number
                if not user_id or user_id == "unknown":
                    # Fallback 1: durable call state (Table Storage)
                    fallback_phone = call_state.get_phone(call_connection_id)
                    if fallback_phone:
                        user_id = fallback_phone
                        session.phone_number = fallback_phone
                        session_store.save_session(session)
                        logger.info(f"Recovered user_id from CallStateStore for {call_connection_id}: {user_id}")

                if not user_id or user_id == "unknown":
                    # Fallback 2 (NUCLEAR): ask ACS directly for current participants
                    try:
                        recovered = await acs_handler.get_phone_raw_id(call_connection_id)
                    except Exception as e:
                        logger.error(
                            f"Error while calling get_phone_raw_id for {call_connection_id}: {e}",
                            exc_info=True,
                        )
                        recovered = None

                    if recovered:
                        user_id = recovered
                        session.phone_number = recovered
                        session_store.save_session(session)
                        call_state.put_phone(call_connection_id, recovered)
                        logger.info(f"Recovered user_id from ACS participants for {call_connection_id}: {user_id}")

                if not user_id or user_id == "unknown":
                    logger.error(
                        f"Unable to determine caller identity for {call_connection_id} "
                        f"even after ACS lookup; skipping TTS response."
                    )
                    return func.HttpResponse(status_code=200)

                logger.info(f"AI response: '{response.response_text}' to user {user_id}")
                await acs_handler.play_and_recognize(call_connection_id, response.response_text, user_id)

            elif "RecognizeFailed" in event_type:
                logger.warning(f"--- RECOGNITION FAILED --- ID: {call_connection_id}")
                result_info = data.get("resultInformation", {})
                error_code = result_info.get("subCode")
                error_msg = result_info.get("message", "Unknown error")
                logger.error(f"Recognition failure: code={error_code}, message={error_msg}")

                # Track number of consecutive failures to avoid infinite retry loops
                session = session_store.get_or_create_session(call_connection_id)
                failures = session.collected_slots.get("_recognize_failures", 0) + 1
                session.collected_slots["_recognize_failures"] = failures
                session_store.save_session(session)

                # If we've failed too many times, apologize and hang up gracefully
                if failures > 2:
                    logger.warning(
                        f"Max recognition retries reached for {call_connection_id} "
                        f"(failures={failures}). Sending apology and ending call."
                    )
                    goodbye_msg = (
                        "Αντιμετωπίζω τεχνικό πρόβλημα με την αναγνώριση της φωνής σας. "
                        "Θα τερματίσω την κλήση και, αν χρειαστεί, μπορείτε να δοκιμάσετε ξανά αργότερα."
                    )
                    await acs_handler.play_and_recognize(call_connection_id, goodbye_msg)
                    await acs_handler.hang_up(call_connection_id)
                    return func.HttpResponse(status_code=200)

                # Otherwise, politely ask the caller to repeat
                retry_msg = "Με συγχωρείτε, δεν σας άκουσα καλά. Μπορείτε να επαναλάβετε;"
                logger.info(
                    f"Retrying recognition for {call_connection_id} "
                    f"(failure count: {failures})"
                )
                await acs_handler.play_and_recognize(call_connection_id, retry_msg)

            elif "CallDisconnected" in event_type:
                logger.info(f"--- CALL DISCONNECTED --- ID: {call_connection_id}")
                session_store.delete_session(call_connection_id)
                call_state.delete(call_connection_id)
            
            elif "PlayCompleted" in event_type:
                logger.info(f"✅ PlayCompleted event received for {call_connection_id}")
                logger.info(f"TTS playback finished. Recognition should now be actively listening.")
            
            elif "PlayFailed" in event_type:
                logger.error(f"❌ PlayFailed event received for {call_connection_id}")
                logger.error(f"Result info: {data.get('resultInformation')}")
            
            else:
                logger.info(f"Other callback event: {event_type}")

        return func.HttpResponse(status_code=200)
    except Exception as e:
        logger.error(f"Error in acs/callback: {str(e)}", exc_info=True)
        return func.HttpResponse(status_code=500)

@app.route(route="dev/diagnostics", methods=["GET"])
async def diagnostics(req: func.HttpRequest) -> func.HttpResponse:
    """Log all environment variables for debugging Azure configuration."""
    logger.info("=" * 80)
    logger.info("DIAGNOSTICS ENDPOINT CALLED - LOGGING ALL ENVIRONMENT VARIABLES")
    logger.info("=" * 80)
    
    critical_vars = [
        "FUNCTIONS_WORKER_RUNTIME",
        "AzureWebJobsFeatureFlags",
        "AzureWebJobsStorage",
        "FUNCTIONS_EXTENSION_VERSION",
        "WEBSITE_SITE_NAME",
        "PYTHON_VERSION",
    ]
    
    env_dump = {}
    for key, value in os.environ.items():
        # Mask sensitive values but show they exist
        if any(secret in key.upper() for secret in ["KEY", "SECRET", "PASSWORD", "TOKEN", "CONNECTION"]):
            if value:
                env_dump[key] = f"<SET: {len(value)} chars>"
            else:
                env_dump[key] = "<EMPTY>"
        else:
            env_dump[key] = value
    
    # Log critical vars prominently
    logger.info("CRITICAL CONFIGURATION:")
    for var in critical_vars:
        val = os.environ.get(var, "<NOT SET>")
        logger.info(f"  {var} = {val}")
    
    # Log all vars
    logger.info("\nALL ENVIRONMENT VARIABLES:")
    for key in sorted(env_dump.keys()):
        logger.info(f"  {key} = {env_dump[key]}")
    
    logger.info("=" * 80)
    
    return func.HttpResponse(
        json.dumps({
            "critical": {var: os.environ.get(var, "<NOT SET>") for var in critical_vars},
            "all_vars": env_dump,
            "function_app_loaded": True,
            "app_instance_id": id(app)
        }, indent=2),
        mimetype="application/json",
        status_code=200
    )

@app.route(route="dev/simulate", methods=["POST"])
async def simulate_call(req: func.HttpRequest) -> func.HttpResponse:
    """Simulate a call for local testing."""
    try:
        body = req.get_json()
        text = body.get("text")
        session_id = body.get("session_id", "simulated-call-123")
        phone = body.get("phone", "306912345678")
        mode = body.get("mode", "live")  # "dry_run" or "live"

        if not text:
            return func.HttpResponse("Missing 'text' in body", status_code=400)

        session = session_store.get_or_create_session(session_id, phone_number=phone)
        
        # In dry_run mode, we might want to preview ticket without creating it
        # For now, we'll still process normally but return more details
        response = await agent.process_utterance(session, text)
        session_store.save_session(session)

        # Build ticket preview if would create ticket
        ticket_preview = None
        if response.flow_state and response.flow_state.last_action == "created_ticket":
            if mode == "dry_run" and session.flow_state:
                ticket_preview = {
                    "would_create": True,
                    "category": session.flow_state.slots.get("category", "unknown"),
                    "urgency": session.flow_state.slots.get("urgency", "medium"),
                    "order_id": session.flow_state.slots.get("order_id"),
                    "summary": session.flow_state.confirmation_summary
                }
            else:
                ticket_preview = {
                    "created": True,
                    "ticket_id": session.ticket_id,
                    "ticket_url": session.ticket_url
                }

        result = {
            "session_id": session_id,
            "user_input": text,
            "agent_intent": response.intent.value if response.intent else "UNKNOWN",
            "agent_response": response.response_text,
            "ticket_id": session.ticket_id,
            "ticket_url": session.ticket_url,
            "history_length": len(session.conversation_history),
            "slots": session.flow_state.slots if session.flow_state else {},
            "next_question": session.flow_state.next_question if session.flow_state else None,
            "ticket_preview": ticket_preview,
            "flow_state": {
                "active_intent": session.flow_state.active_intent.value if session.flow_state and session.flow_state.active_intent else None,
                "missing_slots": session.flow_state.missing_slots if session.flow_state else [],
                "last_action": session.flow_state.last_action if session.flow_state else "",
                "confirmation_summary": session.flow_state.confirmation_summary if session.flow_state else None
            } if session.flow_state else None
        }

        return func.HttpResponse(json.dumps(result, ensure_ascii=False), mimetype="application/json", status_code=200)
    except Exception as e:
        logger.error(f"Error in simulation: {e}")
        return func.HttpResponse(str(e), status_code=500)

@app.route(route="health", methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("Healthy", status_code=200)

@app.route(route="automation/run", methods=["POST"])
async def automation_run(req: func.HttpRequest) -> func.HttpResponse:
    """Execute automated remediation for a GitHub issue (protected by API key)"""
    try:
        # Check API key (simple protection)
        api_key = req.headers.get("X-API-Key") or req.headers.get("Authorization", "").replace("Bearer ", "")
        expected_key = os.getenv("AUTOMATION_API_KEY", "")
        
        if expected_key and api_key != expected_key:
            logger.warning("Unauthorized automation request")
            return func.HttpResponse("Unauthorized", status_code=401)
        
        body = req.get_json()
        issue_number = body.get("issue_number")
        dry_run = body.get("dry_run", True)  # Default to dry-run for safety
        
        if not issue_number:
            return func.HttpResponse("Missing 'issue_number' in body", status_code=400)
        
        # Fetch issue from GitHub
        from src.github_issues import github_client
        from src.remediation_worker import remediation_worker
        
        # In a real implementation, you would fetch the issue from GitHub API
        # For now, we'll accept issue data in the request body
        issue_data = body.get("issue_data", {
            "number": issue_number,
            "labels": body.get("labels", []),
            "body": body.get("body", "")
        })
        
        # Process for automation
        result = await remediation_worker.process_ticket_for_automation(issue_data, dry_run=dry_run)
        
        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, default=str),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error in automation run: {e}", exc_info=True)
        return func.HttpResponse(str(e), status_code=500)
