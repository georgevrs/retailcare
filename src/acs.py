import os
import logging
from typing import Optional

from azure.communication.callautomation import (
    CallAutomationClient,
    TextSource,
    RecognizeInputType,
    CommunicationUserIdentifier,
    PhoneNumberIdentifier,
    UnknownIdentifier,
)

from src.speech import  SpeechConfig
from src.state import   session_store
from src.call_state import call_state

logger = logging.getLogger(__name__)


class ACSCallHandler:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Lazy initialization of the ACS client to prevent startup crashes."""
        if self._client is None:
            connection_string = os.getenv("ACS_CONNECTION_STRING")
            if not connection_string:
                logger.warning("ACS_CONNECTION_STRING is missing or empty. Call control will be disabled.")
                return None
            
            try:
                # Sanitize connection string (remove potential quotes/spaces)
                connection_string = connection_string.strip().strip("'").strip('"')
                # Initialize the client
                self._client = CallAutomationClient.from_connection_string(connection_string)
                logger.info("ACS CallAutomationClient initialized successfully.")
            except Exception as e:
                logger.error(f"CRITICAL: Failed to initialize ACS client: {e}")
                return None
        return self._client

    async def answer_call(self, incoming_call_context: str, callback_url: str):
        client = self.client
        if not client:
            logger.error("Cannot answer_call: ACS client not initialized.")
            return None

        # CRITICAL: Must use a real Speech/Cognitive Services *resource* endpoint, not a region URL.
        # Example of a valid value:
        #   COGNITIVE_SERVICES_ENDPOINT = https://your-speech-resource.cognitiveservices.azure.com
        cognitive_endpoint = os.getenv("COGNITIVE_SERVICES_ENDPOINT")
        if not cognitive_endpoint:
            logger.error(
                "COGNITIVE_SERVICES_ENDPOINT is required and must be a full Speech/Cognitive Services "
                "resource endpoint (e.g. https://<your-speech-resource>.cognitiveservices.azure.com). "
                "Current configuration is invalid and will cause Recognition failures (code 8565)."
            )
            return None

        cognitive_endpoint = cognitive_endpoint.rstrip("/")
        logger.info(f"Using COGNITIVE_SERVICES_ENDPOINT: {cognitive_endpoint}")

        try:
            logger.info(f"Answering call. Callback: {callback_url}")
            logger.info(f"Cognitive Endpoint: {cognitive_endpoint}")

            # answer_call is sync in SDK 1.5.0
            answer_result = client.answer_call(
                incoming_call_context=incoming_call_context,
                callback_url=callback_url,
                cognitive_services_endpoint=cognitive_endpoint
            )
            logger.info(f"Answered call successfully. Connection ID: {answer_result.call_connection_id}")
            logger.info(f"Answer result details - CallConnectionId: {answer_result.call_connection_id}")
            logger.info(f"Callback URL registered: {callback_url}")
            logger.info(f"Cognitive endpoint used: {cognitive_endpoint}")
            return answer_result
        except Exception as e:
            logger.error(f"Error in answer_call: {str(e)}", exc_info=True)
            return None

    async def play_and_recognize(self, call_connection_id: str, text: str, user_id: Optional[str] = None) -> None:
        """
        Play TTS to the caller and start server-side speech recognition for the given call.

        The Azure Communication Services Python SDK requires a `target_participant` when calling
        `start_recognizing_media`, so we must always resolve a stable phone identifier. We:
        - Prefer the provided `user_id` (e.g. '4:+123...')
        - Fallback to the file-backed SessionStore (session.phone_number)
        - Fallback to the durable CallStateStore (for cross-worker resilience)
        """
        client = self.client
        if not client:
            logger.error("Cannot play_and_recognize: ACS client not initialized.")
            return

        logger.info("\n" + "=" * 60)
        logger.info("🎙️ STARTING play_and_recognize")
        logger.info(f"   Call ID: {call_connection_id}")
        logger.info(f"   User ID (initial): {user_id}")
        logger.info(f"   Text: {text[:80]}")
        logger.info("=" * 60 + "\n")

        try:
            call_connection = client.get_call_connection(call_connection_id)

            # Prepare TTS source
            play_source = TextSource(
                text=text,
                voice_name=SpeechConfig.VOICE_NAME,
            )

            # Resolve user_id from session if not provided
            if not user_id or user_id == "unknown":
                try:
                    session = session_store.get_or_create_session(call_connection_id)
                    if getattr(session, "phone_number", None) and session.phone_number != "unknown":
                        user_id = session.phone_number
                        logger.info(f"Recovered user_id from SessionStore: {user_id}")
                except Exception:
                    logger.exception("Failed to recover user_id from SessionStore")

            # Fallback to durable call-state store
            if not user_id or user_id == "unknown":
                recovered = call_state.get_phone(call_connection_id)
                if recovered:
                    user_id = recovered
                    logger.info(f"Recovered user_id from CallStateStore: {user_id}")

            if not user_id or not isinstance(user_id, str):
                logger.error("Cannot start recognition: user_id is unknown or invalid.")
                return

            # Map rawId to a CommunicationIdentifier
            if user_id.startswith("4:"):  # phone number '4:+...'
                phone_val = user_id[2:]
                target = PhoneNumberIdentifier(phone_val)
            elif user_id.startswith("8:"):
                target = CommunicationUserIdentifier(user_id)
            elif user_id.startswith("+"):
                target = PhoneNumberIdentifier(user_id)
            else:
                target = UnknownIdentifier(user_id)

            logger.info(
                "Starting recognition for call %s to target %s (locale=%s, initial_silence=20s, end_silence=3s)",
                call_connection_id,
                user_id,
                getattr(SpeechConfig, "LOCALE", "el-GR"),
            )

            try:
                result = call_connection.start_recognizing_media(
                    input_type=RecognizeInputType.SPEECH,
                    target_participant=target,
                    speech_language=getattr(SpeechConfig, "LOCALE", "el-GR"),
                    play_prompt=play_source,
                    interrupt_prompt=True,
                    operation_context="incoming_utterance",
                    # allow time for TTS + user thinking/response
                    initial_silence_timeout=20,
                    end_silence_timeout=3,
                )
                logger.info(
                    "✅ start_recognizing_media call succeeded for %s; result type=%s",
                    call_connection_id,
                    type(result),
                )
            except Exception as recognition_error:
                logger.error(
                    "❌ start_recognizing_media FAILED for %s: %s",
                    call_connection_id,
                    recognition_error,
                    exc_info=True,
                )
                return

            logger.info("Sent start_recognizing_media for call %s (target=%s)", call_connection_id, user_id)
        except Exception as e:
            logger.error("Error in play_and_recognize for call %s: %s", call_connection_id, e, exc_info=True)

    async def get_call_participants(self, call_connection_id: str):
        """Manually query call participants - useful when CallConnected event is delayed/missing"""
        client = self.client
        if not client:
            logger.error("Cannot get_call_participants: ACS client not initialized.")
            return None
        
        try:
            call_connection = client.get_call_connection(call_connection_id)
            properties = call_connection.get_call_properties()
            logger.info(f"Manually fetched call properties for {call_connection_id}")
            logger.info(f"Call state: {properties.call_connection_state if hasattr(properties, 'call_connection_state') else 'unknown'}")
            return properties
        except Exception as e:
            logger.error(f"Error getting call participants: {e}", exc_info=True)
            return None

    async def get_phone_raw_id(self, call_connection_id: str) -> Optional[str]:
        """
        Best-effort helper to recover the PSTN participant rawId (e.g. '4:+30...') for a call.

        This talks directly to ACS so it works even when our own session or durable state is lost
        (for example after an Azure Functions worker swap).
        """
        client = self.client
        if not client:
            logger.error("Cannot get_phone_raw_id: ACS client not initialized.")
            return None

        try:
            call_connection = client.get_call_connection(call_connection_id)
            participants = list(call_connection.list_participants())
            logger.info(f"Fetched {len(participants)} participants from ACS for call {call_connection_id}")

            for p in participants:
                identifier = getattr(p, "identifier", None)
                if not identifier:
                    continue
                # SDK identifiers typically expose 'raw_id'; fall back to 'rawId' if present.
                raw_id = getattr(identifier, "raw_id", None) or getattr(identifier, "rawId", None)
                if isinstance(raw_id, str) and raw_id.startswith("4:"):
                    logger.info(f"Recovered phone rawId from ACS for {call_connection_id}: {raw_id}")
                    return raw_id

            logger.warning(f"No PSTN (4:+) participant found via ACS for call {call_connection_id}")
            return None
        except Exception as e:
            logger.error(f"Error in get_phone_raw_id for call {call_connection_id}: {e}", exc_info=True)
            return None

    async def hang_up(self, call_connection_id: str):
        client = self.client
        if not client:
            return
        try:
            call_connection = client.get_call_connection(call_connection_id)
            call_connection.hang_up(is_for_everyone=True)
            logger.info(f"Hung up call {call_connection_id}")
        except Exception as e:
            logger.error(f"Error hanging up: {e}")

# Singleton
acs_handler = ACSCallHandler()
