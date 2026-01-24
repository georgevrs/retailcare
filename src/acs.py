import os
import logging
from azure.communication.callautomation import (
    CallAutomationClient,
    CallMediaRecognizeSpeechOptions,
    TextSource
)
from src.speech import SpeechConfig

logger = logging.getLogger(__name__)

class ACSCallHandler:
    def __init__(self):
        connection_string = os.getenv("ACS_CONNECTION_STRING")
        if connection_string:
            self.client = CallAutomationClient.from_connection_string(connection_string)
        else:
            self.client = None
            logger.warning("ACS_CONNECTION_STRING not found")

    async def play_and_recognize(self, call_connection_id: str, text: str, user_id: str):
        if not self.client:
            return

        call_connection = self.client.get_call_connection(call_connection_id)
        
        # Prepare TTS source
        play_source = TextSource(
            text=text,
            voice_name=SpeechConfig.VOICE_NAME
        )

        # Prepare Recognition options (STT)
        recognize_options = CallMediaRecognizeSpeechOptions(
            target_participant=user_id,
            speech_language=SpeechConfig.LOCALE,
            play_prompt=play_source,
            interrupt_prompt=True,
            operation_context="incoming_utterance"
        )

        try:
            call_connection.start_recognizing(recognize_options)
            logger.info(f"Started play_and_recognize for call {call_connection_id}")
        except Exception as e:
            logger.error(f"Error in play_and_recognize: {e}")

    async def hang_up(self, call_connection_id: str):
        if not self.client:
            return
        try:
            call_connection = self.client.get_call_connection(call_connection_id)
            call_connection.hang_up(is_for_everyone=True)
            logger.info(f"Hung up call {call_connection_id}")
        except Exception as e:
            logger.error(f"Error hanging up: {e}")

# Singleton
acs_handler = ACSCallHandler()
