import pytest
from django.contrib.auth.models import User
from hiring.models import HiringRequest, CandidateSession, Round1Question, EvaluationResult
from django.core.exceptions import ValidationError

@pytest.mark.django_db
class TestModels:
    def test_hiring_request_creation(self):
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        hiring_request = HiringRequest.objects.create(
            recruiter=user,
            work_profile='Python Developer',
            years_experience=3,
            difficulty_level='intermediate'
        )
        
        assert hiring_request.work_profile == 'Python Developer'
        assert str(hiring_request) == 'Python Developer (intermediate)'
    
    def test_candidate_session_creation(self):
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        hiring_request = HiringRequest.objects.create(
            recruiter=user,
            work_profile='Python Developer',
            years_experience=3,
            difficulty_level='intermediate'
        )
        
        session = CandidateSession.objects.create(
            hiring_request=hiring_request,
            candidate_email='candidate@example.com'
        )
        
        assert session.token is not None
        assert str(session).startswith('Session')
    
    def test_evaluation_result_calculation(self):
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        hiring_request = HiringRequest.objects.create(
            recruiter=user,
            work_profile='Python Developer',
            years_experience=3,
            difficulty_level='intermediate'
        )
        
        session = CandidateSession.objects.create(hiring_request=hiring_request)
        evaluation = EvaluationResult.objects.create(
            candidate_session=session,
            round1_score=80.0,
            round2_score=70.0
        )
        
        assert evaluation.overall_score == 75.0
        assert evaluation.is_shortlisted == True
        
        # Test failing score
        evaluation2 = EvaluationResult.objects.create(
            candidate_session=session,
            round1_score=50.0,
            round2_score=40.0
        )
        assert evaluation2.is_shortlisted == False