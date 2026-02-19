<<<<<<< HEAD
import pytest
from hiring.services.gemini_client import GeminiClient
from hiring.services.elevenlabs_client import ElevenLabsClient
from hiring.services.stt import STTClient

class TestServices:
    def test_gemini_client_mock_mode(self):
        client = GeminiClient()
        client.mock_mode = True
        
        # Test question generation
        questions = client.generate_questions(
            profile='Python Developer',
            years_experience=3,
            difficulty='intermediate',
            n=5
        )
        
        assert len(questions) > 0
        assert 'question' in questions[0]
        assert 'type' in questions[0]
    
    def test_gemini_client_evaluation(self):
        client = GeminiClient()
        client.mock_mode = True
        
        evaluation = client.evaluate_answer(
            question_rubric='The candidate should mention version control and collaboration',
            candidate_answer='We use Git for version control to work together',
            question_type='short'
        )
        
        assert 'score' in evaluation
        assert 'confidence' in evaluation
        assert 'explanation' in evaluation
        assert isinstance(evaluation['score'], (int, float))
    
    def test_elevenlabs_client_mock_mode(self):
        client = ElevenLabsClient()
        client.mock_mode = True
        
        audio_path = client.synthesize_text_to_audio('Hello, this is a test.')
        
        assert audio_path is not None
        assert audio_path.endswith('.mp3')
    
    def test_stt_client_mock_mode(self):
        client = STTClient()
        client.mock_mode = True
        
        # Create a dummy audio file path
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav') as f:
            transcription = client.transcribe_audio(f.name)
        
        assert 'text' in transcription
        assert 'confidence' in transcription
=======
import pytest
from hiring.services.gemini_client import GeminiClient
from hiring.services.elevenlabs_client import ElevenLabsClient
from hiring.services.stt import STTClient

class TestServices:
    def test_gemini_client_mock_mode(self):
        client = GeminiClient()
        client.mock_mode = True
        
        # Test question generation
        questions = client.generate_questions(
            profile='Python Developer',
            years_experience=3,
            difficulty='intermediate',
            n=5
        )
        
        assert len(questions) > 0
        assert 'question' in questions[0]
        assert 'type' in questions[0]
    
    def test_gemini_client_evaluation(self):
        client = GeminiClient()
        client.mock_mode = True
        
        evaluation = client.evaluate_answer(
            question_rubric='The candidate should mention version control and collaboration',
            candidate_answer='We use Git for version control to work together',
            question_type='short'
        )
        
        assert 'score' in evaluation
        assert 'confidence' in evaluation
        assert 'explanation' in evaluation
        assert isinstance(evaluation['score'], (int, float))
    
    def test_elevenlabs_client_mock_mode(self):
        client = ElevenLabsClient()
        client.mock_mode = True
        
        audio_path = client.synthesize_text_to_audio('Hello, this is a test.')
        
        assert audio_path is not None
        assert audio_path.endswith('.mp3')
    
    def test_stt_client_mock_mode(self):
        client = STTClient()
        client.mock_mode = True
        
        # Create a dummy audio file path
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav') as f:
            transcription = client.transcribe_audio(f.name)
        
        assert 'text' in transcription
        assert 'confidence' in transcription
>>>>>>> 45714fc9bb77db1a37f345b9f3c925e550b03dcb
        assert transcription['success'] == True