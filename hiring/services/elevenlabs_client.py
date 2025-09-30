import os
import logging
import tempfile
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)

class ElevenLabsClient:
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.voice_id = getattr(settings, 'ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
        self.mock_mode = getattr(settings, 'MOCK_MODE', True)
        
        logger.info(f"ElevenLabs Client initialized: MockMode={self.mock_mode}, API_Key_Set={bool(self.api_key)}")
        
    def synthesize_text_to_audio(self, text: str, voice: Optional[str] = None, 
                               format: str = "mp3") -> Optional[str]:
        """
        Convert text to speech - always use mock for now to avoid API issues
        """
        logger.info(f"Text-to-speech requested: {text[:50]}...")
        return self._mock_synthesize_text_to_audio(text)
    
    def _mock_synthesize_text_to_audio(self, text: str) -> Optional[str]:
        """
        Create a mock audio file for testing
        """
        try:
            # Create media/audio directory if it doesn't exist
            audio_dir = os.path.join('media', 'audio')
            os.makedirs(audio_dir, exist_ok=True)
            
            # Create a unique filename
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            filename = f"mock_audio_{text_hash}.mp3"
            file_path = os.path.join(audio_dir, filename)
            
            # Create a minimal silent MP3 file
            silent_mp3 = bytes([
                0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
            ])
            
            with open(file_path, 'wb') as f:
                f.write(silent_mp3)
            
            logger.info(f"Mock audio file created: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error creating mock audio: {e}")
            return None