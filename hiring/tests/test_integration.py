import pytest
import json
from django.contrib.auth.models import User
from django.urls import reverse
from hiring.models import HiringRequest, CandidateSession, Round1Answer, EvaluationResult

@pytest.mark.django_db
class TestIntegration:
    def test_full_candidate_flow(self, client, settings):
        # Setup
        settings.MOCK_MODE = True
        
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        hiring_request = HiringRequest.objects.create(
            recruiter=user,
            work_profile='Python Developer',
            years_experience=3,
            difficulty_level='intermediate',
            number_of_questions_round1=2,
            number_of_questions_round2=2
        )
        
        # Create questions
        from hiring.models import Round1Question, Round2Question
        q1 = Round1Question.objects.create(
            hiring_request=hiring_request,
            question_text='What is Python?',
            question_type='short',
            model_answer='Python is a programming language'
        )
        q2 = Round1Question.objects.create(
            hiring_request=hiring_request,
            question_text='What is Git?',
            question_type='short', 
            model_answer='Git is a version control system'
        )
        
        # Create candidate session
        session = CandidateSession.objects.create(hiring_request=hiring_request)
        
        # Test Round 1 access
        response = client.get(reverse('candidate_round1', args=[session.token]))
        assert response.status_code == 200
        
        # Test Round 1 submission
        answers = {
            f'question_{q1.id}': 'Python is a programming language',
            f'question_{q2.id}': 'Git is for version control'
        }
        
        response = client.post(
            reverse('submit_round1', args=[session.token]),
            data=json.dumps({'answers': answers}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] == True
        
        # Check that answers were saved
        assert Round1Answer.objects.filter(candidate_session=session).count() == 2
        
        # Check evaluation result
        evaluation = EvaluationResult.objects.get(candidate_session=session)
        assert evaluation.round1_score is not None
        
        # Test Round 2 access
        session.refresh_from_db()
        if session.completed_round1 and evaluation.round1_score >= 60:
            response = client.get(reverse('candidate_round2', args=[session.token]))
            assert response.status_code == 200
    
    def test_recruiter_flow(self, client):
        # Create and login user
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        client.force_login(user)
        
        # Test dashboard access
        response = client.get(reverse('recruiter_dashboard'))
        assert response.status_code == 200
        
        # Test hiring request creation
        response = client.post(reverse('create_hiring_request'), {
            'work_profile': 'Test Developer',
            'years_experience': 2,
            'difficulty_level': 'beginner',
            'number_of_questions_round1': 5,
            'number_of_questions_round2': 3
        })
        
        # Should redirect to dashboard on success
        assert response.status_code == 302
        assert HiringRequest.objects.filter(work_profile='Test Developer').exists()