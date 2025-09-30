import os
import logging
import tempfile
from typing import Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)

class STTClient:
    """
    Speech-to-Text client for transcribing audio files.
    Supports both OpenAI Whisper API and mock mode for development.
    """
    
    def __init__(self):
        """Initialize the STT client with configuration from settings."""
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.mode = getattr(settings, 'STT_MODE', 'mock')
        self.mock_mode = getattr(settings, 'MOCK_MODE', True)
        
        # Log initialization details
        logger.info(f"STT Client initialized: Mode={self.mode}, MockMode={self.mock_mode}, API_Key_Present={bool(self.api_key)}")
        
        # Configure OpenAI if API key is available and not in mock mode
        if not self.mock_mode and self.api_key and self.mode == 'remote':
            try:
                import openai
                openai.api_key = self.api_key
                logger.info("OpenAI API configured successfully")
            except ImportError:
                logger.error("OpenAI package not installed. Falling back to mock mode.")
                self.mock_mode = True
    
    def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file to text using the configured method.
        
        Args:
            audio_file_path: Path to the audio file to transcribe
            
        Returns:
            Dictionary containing transcription results and metadata
        """
        # Validate file exists
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return {
                "text": "",
                "confidence": 0.0,
                "success": False,
                "error": "Audio file not found"
            }
        
        # Use mock mode if configured
        if self.mock_mode:
            logger.info("Using mock transcription mode")
            return self._mock_transcribe_audio(audio_file_path)
        
        # Use remote Whisper API if configured
        if self.mode == 'remote' and self.api_key:
            logger.info("Using OpenAI Whisper API for transcription")
            return self._transcribe_with_whisper_api(audio_file_path)
        else:
            # Fallback to local mock transcription
            logger.info("Falling back to local mock transcription")
            return self._transcribe_local_fallback(audio_file_path)
    
    def _transcribe_with_whisper_api(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Transcribe audio using OpenAI Whisper API with enhanced error handling.
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Dictionary with transcription results
        """
        try:
            import openai
            
            # Verify file size and type
            file_size = os.path.getsize(audio_file_path)
            if file_size > 25 * 1024 * 1024:  # 25MB limit for Whisper
                logger.warning(f"File too large for Whisper API: {file_size} bytes")
                return self._transcribe_local_fallback(audio_file_path)
            
            with open(audio_file_path, "rb") as audio_file:
                # Call Whisper API with optimized parameters for interview audio
                transcript = openai.Audio.transcribe(
                    model="whisper-1",
                    file=audio_file,
                    language="en",  # Specify English for better accuracy
                    temperature=0.1,  # Low temperature for consistent results
                    prompt="This is a technical interview response. Please transcribe accurately with proper technical terms and punctuation."
                )
            
            transcription_text = transcript.text.strip()
            
            logger.info(f"Whisper API transcription successful. Text length: {len(transcription_text)}")
            
            return {
                "text": transcription_text,
                "confidence": 0.95,  # Whisper is generally very accurate
                "success": True,
                "word_count": len(transcription_text.split()),
                "char_count": len(transcription_text),
                "is_mock": False
            }
            
        except Exception as e:
            logger.error(f"Error transcribing with Whisper API: {str(e)}")
            # Fallback to local transcription
            return self._transcribe_local_fallback(audio_file_path)
    
    def _transcribe_local_fallback(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Local fallback transcription when API is unavailable.
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Dictionary with mock transcription results
        """
        try:
            # In a production environment, you might use a local Whisper model here
            # For now, return a descriptive mock transcription
            mock_text = "This is a mock transcription of an interview response. In a real implementation, this would be the actual transcribed text from the audio recording."
            
            logger.info("Using local fallback transcription")
            
            return {
                "text": mock_text,
                "confidence": 0.7,
                "success": True,
                "is_mock": True,
                "word_count": len(mock_text.split()),
                "char_count": len(mock_text)
            }
        except Exception as e:
            logger.error(f"Error in local transcription fallback: {str(e)}")
            return {
                "text": "",
                "confidence": 0.0,
                "success": False,
                "error": str(e),
                "is_mock": True
            }
    
    def _mock_transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Mock transcription for testing and development.
        Generates realistic interview responses based on the audio file.
        
        Args:
            audio_file_path: Path to the audio file (used for deterministic responses)
            
        Returns:
            Dictionary with mock transcription results
        """
        try:
            # Realistic interview responses for different scenarios
            technical_responses = [
                "I have extensive experience with loading optimization and repeat processes in software development. In my previous role, I implemented lazy loading techniques that improved application performance by 40%.",
                "When dealing with repeat processes, I focus on creating idempotent systems that can handle retries safely. I've worked with message queues and background jobs to manage repetitive tasks efficiently.",
                "My approach to loading strategies involves analyzing user behavior patterns and implementing progressive loading. For repeatable processes, I ensure proper error handling and state management.",
                "I believe that efficient loading is crucial for user experience. I've implemented caching strategies and CDN optimization to reduce load times. For repeat processes, I use circuit breakers and exponential backoff.",
                "In my experience, the key to handling repeat processes is proper logging and monitoring. I've set up alert systems that notify us when processes fail repeatedly, allowing for quick intervention."
            ]
            
            behavioral_responses = [
                "I approach technical challenges systematically, first understanding the requirements, then designing a solution, implementing it, and finally testing thoroughly.",
                "Collaboration is key in software development. I regularly conduct code reviews and pair programming sessions to ensure code quality and knowledge sharing.",
                "I believe in continuous learning and regularly update my skills through online courses, tech talks, and hands-on projects with new technologies.",
                "When facing tight deadlines, I prioritize tasks based on impact and complexity, focusing on delivering the most critical features first while maintaining code quality.",
                "I value clean code principles and always strive to write maintainable, well-documented code that other developers can easily understand and extend."
            ]
            
            # Use file path to generate deterministic but varied responses
            import hashlib
            file_hash = hashlib.md5(audio_file_path.encode()).hexdigest()
            hash_value = int(file_hash, 16)
            
            # Alternate between technical and behavioral responses
            response_pool = technical_responses if hash_value % 2 == 0 else behavioral_responses
            response_index = hash_value % len(response_pool)
            
            transcribed_text = response_pool[response_index]
            
            # Check if the response indicates a request to repeat the question
            is_repeat_request = any(keyword in transcribed_text.lower() for keyword in 
                                  ['repeat', 'again', 'pardon', 'sorry', 'clarify', 'understand'])
            
            logger.info(f"Mock transcription generated. Repeat request: {is_repeat_request}")
            
            return {
                "text": transcribed_text,
                "confidence": 0.85,
                "success": True,
                "is_mock": True,
                "is_repeat_request": is_repeat_request,
                "word_count": len(transcribed_text.split()),
                "char_count": len(transcribed_text)
            }
            
        except Exception as e:
            logger.error(f"Error in mock transcription: {str(e)}")
            # Fallback to basic response
            return {
                "text": "I would be happy to discuss my experience with loading and repeat processes in software development.",
                "confidence": 0.8,
                "success": True,
                "is_mock": True,
                "is_repeat_request": False,
                "word_count": 15,
                "char_count": 80
            }