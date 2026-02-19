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
    options = models.JSONField(null=True, blank=True)
    correct_option_index = models.IntegerField(null=True, blank=True)
    model_answer = models.TextField()
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
    termination_reason = models.CharField(max_length=255, default="N/A")
    is_terminated = models.BooleanField(default=False)
    system_check_completed = models.BooleanField(default=False)
    
    # Enhanced proctoring fields
    camera_enabled = models.BooleanField(default=False)
    audio_enabled = models.BooleanField(default=False)
    proctoring_warnings_count = models.IntegerField(default=0)
    last_violation_time = models.FloatField(default=0)
    camera_warnings_count = models.IntegerField(default=0)
    voice_warnings_count = models.IntegerField(default=0)
    tab_warnings_count = models.IntegerField(default=0)
    screen_share_warnings_count = models.IntegerField(default=0)
    last_proctoring_check = models.DateTimeField(auto_now=True)
    is_proctoring_active = models.BooleanField(default=True)
    screen_sharing_blocked = models.BooleanField(default=False)
    screen_sharing_detected = models.BooleanField(default=False)

    def get_next_question(self):
        questions = self.hiring_request.round2_questions.all().order_by('question_order')
        current_index = self.current_question_index or 0
        if current_index < questions.count():
            return questions[current_index]
        return None

    def add_proctoring_violation(self, violation_type, details="", screenshot_path=None, severity="warning"):
        """Add a proctoring violation with enhanced categorization"""
        violation = ProctoringViolation.objects.create(
            candidate_session=self,
            violation_type=violation_type,
            violation_details=details,
            screenshot_path=screenshot_path,
            severity=severity
        )
        
        # Increment specific warning counters
        if "camera" in violation_type or "multiple_people" in violation_type or "person_left" in violation_type or "head_turn" in violation_type:
            self.camera_warnings_count += 1
        elif "voice" in violation_type or "audio" in violation_type:
            self.voice_warnings_count += 1
        elif "tab" in violation_type:
            self.tab_warnings_count += 1
        elif "screen_share" in violation_type:
            self.screen_share_warnings_count += 1
        
        # Increment total warning count
        self.proctoring_warnings_count += 1
        violation.is_warning_issued = True
        
        # Immediate termination: multiple people, electronic device (no warnings)
        if violation_type in ('multiple_people', 'mobile_phone'):
            self.is_terminated = True
            if violation_type == 'multiple_people':
                self.termination_reason = "Test terminated: Multiple people detected in camera feed"
            else:
                self.termination_reason = "Test terminated: Electronic device detected in camera feed"
            violation.violation_details += " - TEST TERMINATED"
        # General 3-warnings threshold for other violation types (except extreme_head_turn uses its own rule)
        elif violation_type != 'extreme_head_turn' and self.proctoring_warnings_count >= 3:
            self.is_terminated = True
            if self.camera_warnings_count >= 2:
                self.termination_reason = "Terminated due to camera proctoring violations"
            elif self.voice_warnings_count >= 2:
                self.termination_reason = "Terminated due to voice proctoring violations"
            elif self.tab_warnings_count >= 2:
                self.termination_reason = "Terminated due to tab switching violations"
            elif self.screen_share_warnings_count >= 1:
                self.termination_reason = "Terminated due to screen sharing violations"
            else:
                self.termination_reason = f"Terminated due to multiple proctoring violations ({self.proctoring_warnings_count} warnings)"
            violation.violation_details += " - TEST TERMINATED"
        
        violation.save()
        self.save()
        
        # Head turn: max 2 warnings, 3rd occurrence = terminate (check after violation is saved)
        if violation_type == 'extreme_head_turn':
            head_turn_count = self.proctoring_violations.filter(violation_type='extreme_head_turn').count()
            if head_turn_count >= 3:
                self.is_terminated = True
                self.termination_reason = "Test terminated: Looking away from screen (head turn) - third violation"
                violation.violation_details += " - TEST TERMINATED"
                violation.save()
                self.save()
        
        return self.proctoring_warnings_count
        
    
    def mark_screen_sharing_detected(self):
        """Mark that screen sharing was detected"""
        self.screen_sharing_detected = True
        self.screen_sharing_blocked = True
        self.save()
    
    def mark_screen_sharing_resolved(self):
        """Mark that screen sharing is no longer detected"""
        self.screen_sharing_detected = False
        self.screen_sharing_blocked = False
        self.save()
    
    def __str__(self):
        return f"Session {self.token}"


class Round1Answer(models.Model):
    candidate_session = models.ForeignKey(CandidateSession, on_delete=models.CASCADE, related_name='round1_answers')
    question = models.ForeignKey(Round1Question, on_delete=models.CASCADE)
    candidate_answer = models.TextField()
    score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    feedback = models.TextField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
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
    keywords_matched = models.JSONField(default=list, blank=True)
    improvement_suggestions = models.JSONField(default=list, blank=True)
    evaluation_confidence = models.FloatField(default=0.0)
    
    class Meta:
        unique_together = ['candidate_session', 'question']


class EvaluationResult(models.Model):
    candidate_session = models.OneToOneField(CandidateSession, on_delete=models.CASCADE)
    round1_score = models.FloatField(null=True, blank=True)
    round2_score = models.FloatField(null=True, blank=True)
    overall_score = models.FloatField(null=True, blank=True)
    is_shortlisted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    evaluation_notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.candidate_session.is_terminated:
            self.overall_score = None
            self.round1_score = None
            self.round2_score = None
            self.is_shortlisted = False
        else:
            if self.round1_score is not None and self.round2_score is not None:
                self.overall_score = (self.round1_score + self.round2_score) / 2
            elif self.round1_score is not None:
                self.overall_score = self.round1_score
            elif self.round2_score is not None:
                self.overall_score = self.round2_score

            self.is_shortlisted = self.overall_score >= 60 if self.overall_score is not None else False

        super().save(*args, **kwargs)


class ProctoringViolation(models.Model):
    VIOLATION_TYPES = [
        ('no_camera', 'No Camera Detected'),
        ('multiple_people', 'Multiple People Detected'),
        ('mobile_phone', 'Mobile Phone Detected'),  # ENHANCED
        ('person_left', 'Person Left Camera View'),
        ('looking_away', 'Looking Away From Screen'),
        ('extreme_head_turn', 'Extreme Head Turn'),
        ('face_occluded', 'Face Occluded/Covered'),  # NEW
        ('camera_blocked', 'Camera Blocked'),  # NEW
        ('tab_switch', 'Tab Switching'),
        ('audio_violation', 'Audio Violation'),
        ('right_click', 'Right Click on Content'),
        ('tab_right_click', 'Right Click on Test Tabs'),
        ('screen_share', 'Screen Sharing Detected'),
    ]
    
    SEVERITY_CHOICES = [
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('terminal', 'Terminal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate_session = models.ForeignKey('CandidateSession', on_delete=models.CASCADE, related_name='proctoring_violations')
    violation_type = models.CharField(max_length=30, choices=VIOLATION_TYPES)
    violation_timestamp = models.DateTimeField(auto_now_add=True)
    violation_details = models.TextField(blank=True, null=True)
    screenshot_path = models.CharField(max_length=500, blank=True, null=True)
    is_warning_issued = models.BooleanField(default=False)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='warning')
    confidence_score = models.FloatField(default=0.0)
    
    class Meta:
        ordering = ['-violation_timestamp']
    
    def __str__(self):
        return f"{self.candidate_session.token} - {self.violation_type} ({self.severity})"