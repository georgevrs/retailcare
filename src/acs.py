import os
import logging
from azure.communication.callautomation import (
    CallAutomationClient,
    TextSource,
    RecognizeInputType,
    CommunicationUserIdentifier,
    PhoneNumberIdentifier,
    UnknownIdentifier
)
from src.speech import SpeechConfig

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
        
        # Use the multi-service Cognitive Services endpoint
        # This should point to your Cognitive Services resource (not OpenAI-specific)
        cognitive_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not cognitive_endpoint:
            # Fallback to constructing from Speech region
            speech_region = os.getenv("SPEECH_REGION", "francecentral")
            cognitive_endpoint = f"https://{speech_region}.cognitiveservices.azure.com/"
        else:
            # Ensure proper format (remove trailing slash for consistency)
            cognitive_endpoint = cognitive_endpoint.rstrip("/")
        
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
            return answer_result
        except Exception as e:
            logger.error(f"Error in answer_call: {str(e)}", exc_info=True)
            return None

    async def play_and_recognize(self, call_connection_id: str, text: str, user_id: str):
        client = self.client
        if not client:
            logger.error("Cannot play_and_recognize: ACS client not initialized.")
            return

        try:
            call_connection = client.get_call_connection(call_connection_id)
            
            # Prepare TTS source
            play_source = TextSource(
                text=text,
                voice_name=SpeechConfig.VOICE_NAME
            )
            
            if not user_id or user_id == "unknown":
                logger.error("Cannot start recognition: user_id is unknown.")
                return

            # Determine the type of identifier from the rawId
            if user_id.startswith("4:"):
                # Phone number: "4:+3069..." -> "+3069..."
                phone_val = user_id[2:]
                target = PhoneNumberIdentifier(phone_val)
            elif user_id.startswith("8:acs:"):
                target = CommunicationUserIdentifier(user_id)
            else:
                # Fallback to phone number if it looks like one, else unknown
                if user_id.startswith("+"):
                    target = PhoneNumberIdentifier(user_id)
                else:
                    target = UnknownIdentifier(user_id)

            logger.info(f"Starting recognition for target: {user_id}")

            # In Python SDK 1.5.0, the method is start_recognizing_media
            call_connection.start_recognizing_media(
                input_type=RecognizeInputType.SPEECH,
                target_participant=target,
                speech_language=SpeechConfig.LOCALE,
                play_prompt=play_source,
                interrupt_prompt=True,
                operation_context="incoming_utterance",
                end_silence_timeout=2
            )
            logger.info(f"Sent start_recognizing_media for call {call_connection_id}. Text: {text[:30]}...")
        except Exception as e:
            logger.error(f"Error in play_and_recognize: {e}", exc_info=True)

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
