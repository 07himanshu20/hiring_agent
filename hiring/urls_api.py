<<<<<<< HEAD
from django.urls import path
from . import views

urlpatterns = [
    path('generate-questions/', views.api_generate_questions, name='api_generate_questions'),
    path('evaluate-answer/', views.api_evaluate_answer, name='api_evaluate_answer'),
    path('synthesize-speech/', views.api_synthesize_speech, name='api_synthesize_speech'),
=======
from django.urls import path
from . import views

urlpatterns = [
    path('generate-questions/', views.api_generate_questions, name='api_generate_questions'),
    path('evaluate-answer/', views.api_evaluate_answer, name='api_evaluate_answer'),
    path('synthesize-speech/', views.api_synthesize_speech, name='api_synthesize_speech'),
>>>>>>> 45714fc9bb77db1a37f345b9f3c925e550b03dcb
]