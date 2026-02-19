<<<<<<< HEAD
from django.urls import path
from . import views

app_name = 'hiring'

urlpatterns = [
    # Welcome Page
    path('', views.welcome_page, name='welcome'),
    
    # Recruiter URLs
    path('recruiter/dashboard/', views.recruiter_dashboard, name='recruiter_dashboard'),
    path('recruiter/create/', views.create_hiring_request, name='create_hiring_request'),
    path('recruiter/results/<uuid:request_id>/', views.view_results, name='view_results'),
    path('recruiter/results/<uuid:request_id>/json/', views.get_candidate_results, name='get_candidate_results'),
    path('terminated/', views.terminated_view, name='terminated'),
    
    # Candidate URLs
    path('candidate/<uuid:token>/system-check/', views.candidate_system_check, name='candidate_system_check'),
    path('candidate/<uuid:token>/round1/', views.candidate_round1, name='candidate_round1'),
    path('candidate/<uuid:token>/round1/submit/', views.submit_round1, name='submit_round1'),
    path('candidate/<uuid:token>/round2/', views.candidate_round2, name='candidate_round2'),
    path('candidate/<uuid:token>/round2/submit/', views.submit_audio_answer, name='submit_audio_answer'),
    path('candidate/<uuid:token>/results/', views.candidate_results, name='candidate_results'),
    
    # Display Round 1 Test (string token)
    path('candidate/<str:token>/round1/', views.display_round1_test, name='round1_test'),

    # System Check API
    path('api/system-check/<uuid:token>/complete/', views.api_complete_system_check, name='api_complete_system_check'),
    path('validate-system/', views.validate_system_requirements, name='validate_system'),
    path('api/enhanced-validate-system/', views.enhanced_validate_system, name='enhanced_validate_system'),

    # Proctoring API Endpoints
    path('api/proctoring/<uuid:token>/initialize/', views.api_initialize_proctoring, name='api_initialize_proctoring'),
    path('api/proctoring/<uuid:token>/process-frame/', views.api_process_proctoring_frame, name='api_process_proctoring_frame'),
    
    # Main API Endpoints
    path('api/generate-questions/', views.api_generate_questions, name='api_generate_questions'),
    path('api/evaluate-answer/', views.api_evaluate_answer, name='api_evaluate_answer'),
    path('api/synthesize-speech/', views.api_synthesize_speech, name='api_synthesize_speech'),
    path('api/terminate-test/', views.api_terminate_test, name='api_terminate_test'),

    # Enhanced Proctoring API Endpoints
    path('api/proctoring/<uuid:token>/record-violation/', views.api_record_violation, name='api_record_violation'),
    path('api/proctoring/<uuid:token>/check-screen-sharing/', views.api_check_screen_sharing_during_test, name='api_check_screen_sharing_during_test'),
    path('api/proctoring/<uuid:token>/mark-screen-sharing-detected/', views.api_mark_screen_sharing_detected, name='api_mark_screen_sharing_detected'),
    path('api/proctoring/<uuid:token>/mark-screen-sharing-resolved/', views.api_mark_screen_sharing_resolved, name='api_mark_screen_sharing_resolved'),
    
    # NEW: Force termination endpoint
    path('api/proctoring/<uuid:token>/force-terminate-sharing/', views.api_force_terminate_sharing, name='api_force_terminate_sharing'),
=======
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
>>>>>>> 45714fc9bb77db1a37f345b9f3c925e550b03dcb
]