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
        Enhanced mock transcription for testing with more varied and realistic responses.
        """
        try:
            # More realistic and varied interview responses that would get different scores
            high_score_responses = [
                "I have extensive experience with system optimization and repeatable processes. In my previous role at TechCorp, I implemented lazy loading techniques that improved application performance by 40% and reduced server load significantly. I also designed idempotent APIs that could safely handle retries without side effects.",
                "When dealing with repeat processes, I focus on creating robust systems with proper error handling and state management. I've worked extensively with message queues like RabbitMQ and background job processors to manage repetitive tasks efficiently while ensuring data consistency.",
                "My approach to system architecture involves analyzing performance bottlenecks and implementing appropriate caching strategies. For repeatable processes, I ensure they are stateless where possible and implement proper logging and monitoring to track their execution and identify issues early.",
                "I believe that efficient system design is crucial for scalability. I've implemented various optimization techniques including database indexing, query optimization, and CDN integration. For repeat processes, I use circuit breakers and exponential backoff to handle failures gracefully.",
            ]
            
            medium_score_responses = [
                "I have experience with loading optimization and have worked on improving application performance. I've used caching and some optimization techniques to make systems faster.",
                "For repeat processes, I try to make sure they can run multiple times safely. I've used some background job systems and message queues in my projects.",
                "I know that performance is important for user experience. I've implemented some basic optimization techniques and try to follow best practices for system design.",
                "When working with repetitive tasks, I focus on making them reliable and ensuring they handle errors properly. I've used logging to track issues and retry mechanisms for failures.",
            ]
            
            low_score_responses = [
                "I think loading is important for websites. I've done some work on making pages load faster by optimizing images and using CDNs.",
                "For processes that repeat, I make sure they work correctly. I've written scripts that run multiple times and check if they complete successfully.",
                "I know that system performance matters. I try to write efficient code and use tools that help with optimization when I can.",
                "I've worked on tasks that need to run multiple times. I make sure they have error handling and can recover from failures when possible.",
            ]
            
            # Use file path to generate deterministic but varied responses
            import hashlib
            file_hash = hashlib.md5(audio_file_path.encode()).hexdigest()
            hash_value = int(file_hash, 16)
            
            # Distribute responses across quality levels
            response_quality = hash_value % 10
            if response_quality >= 8:  # 20% high quality
                response_pool = high_score_responses
            elif response_quality >= 5:  # 30% medium quality  
                response_pool = medium_score_responses
            else:  # 50% low quality
                response_pool = low_score_responses
                
            response_index = hash_value % len(response_pool)
            transcribed_text = response_pool[response_index]
            
            logger.info(f"Mock transcription generated. Quality level: {'high' if response_quality >= 8 else 'medium' if response_quality >= 5 else 'low'}")
            
            return {
                "text": transcribed_text,
                "confidence": 0.85,
                "success": True,
                "is_mock": True,
                "word_count": len(transcribed_text.split()),
                "char_count": len(transcribed_text)
            }
            
        except Exception as e:
            logger.error(f"Error in mock transcription: {str(e)}")
            # Fallback to basic response
            return {
                "text": "I would be happy to discuss my experience with system optimization and repeatable processes in software development.",
                "confidence": 0.8,
                "success": True,
                "is_mock": True,
                "word_count": 15,
                "char_count": 80
            }
