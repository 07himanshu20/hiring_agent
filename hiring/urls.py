from django.urls import path
from . import views

app_name = 'hiring'  # Add this line

urlpatterns = [
    # Welcome page
    path('', views.welcome_page, name='welcome'),
    
    # Recruiter URLs
    path('recruiter/dashboard/', views.recruiter_dashboard, name='recruiter_dashboard'),
    path('recruiter/create/', views.create_hiring_request, name='create_hiring_request'),
    path('recruiter/results/<int:request_id>/', views.view_results, name='view_results'),
    path('recruiter/results/<int:request_id>/json/', views.get_candidate_results, name='get_candidate_results'),
    
    # Candidate URLs
    path('candidate/<uuid:token>/round1/', views.candidate_round1, name='candidate_round1'),
    path('candidate/<uuid:token>/round1/submit/', views.submit_round1, name='submit_round1'),
    path('candidate/<uuid:token>/round2/', views.candidate_round2, name='candidate_round2'),
    path('candidate/<uuid:token>/round2/submit/', views.submit_audio_answer, name='submit_audio_answer'),  # Add this line
    path('candidate/<uuid:token>/results/', views.candidate_results, name='candidate_results'),
    
    # API endpoints
    path('api/generate-questions/', views.api_generate_questions, name='api_generate_questions'),
    path('api/evaluate-answer/', views.api_evaluate_answer, name='api_evaluate_answer'),
    path('api/synthesize-speech/', views.api_synthesize_speech, name='api_synthesize_speech'),
]