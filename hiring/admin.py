from django.contrib import admin
from .models import HiringRequest, CandidateSession, Round1Question, Round1Answer, Round2Question, Round2Answer, EvaluationResult

@admin.register(HiringRequest)
class HiringRequestAdmin(admin.ModelAdmin):
    list_display = ['work_profile', 'years_experience', 'difficulty_level', 'recruiter', 'created_at']
    list_filter = ['difficulty_level', 'created_at']
    search_fields = ['work_profile', 'recruiter__username']

@admin.register(CandidateSession)
class CandidateSessionAdmin(admin.ModelAdmin):
    list_display = ['token', 'hiring_request', 'candidate_email', 'created_at', 'completed_round1', 'completed_round2']
    list_filter = ['completed_round1', 'completed_round2', 'created_at']
    search_fields = ['token', 'candidate_email']

@admin.register(Round1Question)
class Round1QuestionAdmin(admin.ModelAdmin):
    list_display = ['hiring_request', 'question_type', 'created_at']
    list_filter = ['question_type', 'created_at']

@admin.register(Round1Answer)
class Round1AnswerAdmin(admin.ModelAdmin):
    list_display = ['candidate_session', 'question', 'score', 'created_at']
    list_filter = ['score', 'created_at']

@admin.register(Round2Question)
class Round2QuestionAdmin(admin.ModelAdmin):
    list_display = ['hiring_request', 'question_order', 'created_at']
    list_filter = ['created_at']

@admin.register(Round2Answer)
class Round2AnswerAdmin(admin.ModelAdmin):
    list_display = ['candidate_session', 'question', 'score', 'repeat_count', 'created_at']
    list_filter = ['score', 'repeat_count', 'created_at']

@admin.register(EvaluationResult)
class EvaluationResultAdmin(admin.ModelAdmin):
    list_display = ['candidate_session', 'round1_score', 'round2_score', 'overall_score', 'is_shortlisted', 'created_at']
    list_filter = ['is_shortlisted', 'created_at']
    search_fields = ['candidate_session__token']