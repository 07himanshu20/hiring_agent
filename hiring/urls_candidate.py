from django.urls import path
from . import views

urlpatterns = [
    path('<uuid:token>/round1/', views.candidate_round1, name='candidate_round1'),
    path('<uuid:token>/round1/submit/', views.submit_round1, name='submit_round1'),
    path('<uuid:token>/round2/', views.candidate_round2, name='candidate_round2'),
    path('<uuid:token>/round2/audio/', views.submit_audio_answer, name='upload_audio_answer'),
    path('<uuid:token>/results/', views.candidate_results, name='candidate_results'),
    path('<uuid:token>/results/', views.candidate_results, name='candidate_results'),
]