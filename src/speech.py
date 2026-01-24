import os

class SpeechConfig:
    # Locale for Greek
    LOCALE = "el-GR"
    
    # Text-to-Speech Voice
    VOICE_NAME = "el-GR-AthinaNeural"
    
    @staticmethod
    def get_speech_key():
        return os.getenv("SPEECH_KEY")

    @staticmethod
    def get_speech_region():
        return os.getenv("SPEECH_REGION")
