import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class HiringRequest(models.Model):
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('expert', 'Expert'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recruiter = models.ForeignKey(User, on_delete=models.CASCADE)
    work_profile = models.CharField(max_length=200)
    years_experience = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(50)])
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    number_of_questions_round1 = models.IntegerField(default=20, validators=[MinValueValidator(1)])
    number_of_questions_round2 = models.IntegerField(default=5, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.work_profile} ({self.difficulty_level})"

class Round1Question(models.Model):
    QUESTION_TYPES = [
        ('mcq', 'Multiple Choice'),
        ('short', 'Short Answer'),
    ]
    
    hiring_request = models.ForeignKey(HiringRequest, on_delete=models.CASCADE, related_name='round1_questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES)
    options = models.JSONField(null=True, blank=True)  # For MCQ: list of options
    correct_option_index = models.IntegerField(null=True, blank=True)  # For MCQ: index of correct option
    model_answer = models.TextField()  # Expected answer/rubric
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']

class CandidateSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hiring_request = models.ForeignKey(HiringRequest, on_delete=models.CASCADE)
    candidate_email = models.EmailField(null=True, blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_round1 = models.BooleanField(default=False)
    completed_round2 = models.BooleanField(default=False)
    current_question_index = models.IntegerField(default=0, null=True, blank=True)

    def get_next_question(self):
        questions = self.hiring_request.round2_questions.all().order_by('question_order')
        current_index = self.current_question_index or 0
        if current_index < questions.count():
            return questions[current_index]
        return None

    
    
    def __str__(self):
        return f"Session {self.token}"

class Round1Answer(models.Model):
    candidate_session = models.ForeignKey(CandidateSession, on_delete=models.CASCADE, related_name='round1_answers')
    question = models.ForeignKey(Round1Question, on_delete=models.CASCADE)
    candidate_answer = models.TextField()
    score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['candidate_session', 'question']

class Round2Question(models.Model):
    hiring_request = models.ForeignKey(HiringRequest, on_delete=models.CASCADE, related_name='round2_questions')
    question_text = models.TextField()
    question_order = models.IntegerField(default=0)
    model_answer = models.TextField()
    audio_file_path = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['question_order']

class Round2Answer(models.Model):
    candidate_session = models.ForeignKey(CandidateSession, on_delete=models.CASCADE, related_name='round2_answers')
    question = models.ForeignKey(Round2Question, on_delete=models.CASCADE)
    audio_response_path = models.CharField(max_length=500, null=True, blank=True)
    transcribed_text = models.TextField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    feedback = models.TextField(null=True, blank=True)
    repeat_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    keywords_matched = models.JSONField(default=list, blank=True)  # Store matched keywords
    improvement_suggestions = models.JSONField(default=list, blank=True)  # Store suggestions
    evaluation_confidence = models.FloatField(default=0.0)  # Gemini's confidence in evaluation
    
    class Meta:
        unique_together = ['candidate_session', 'question']

class EvaluationResult(models.Model):
    candidate_session = models.OneToOneField(CandidateSession, on_delete=models.CASCADE)
    round1_score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    round2_score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    overall_score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    is_shortlisted = models.BooleanField(default=False)
    evaluation_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Calculate overall score as average of round1 and round2
        if self.round1_score is not None and self.round2_score is not None:
            self.overall_score = (self.round1_score + self.round2_score) / 2
        elif self.round1_score is not None:
            self.overall_score = self.round1_score
        elif self.round2_score is not None:
            self.overall_score = self.round2_score
        
        # Shortlist if overall score >= 60
        self.is_shortlisted = self.overall_score >= 60 if self.overall_score is not None else False
        super().save(*args, **kwargs)