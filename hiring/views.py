import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.conf import settings
from .models import *
from .forms import *
from .services.gemini_client import GeminiClient
from .services.elevenlabs_client import ElevenLabsClient
from .services.stt import STTClient
import time
import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.conf import settings
from .models import *
from .services.screen_sharing_detector import screen_sharing_detector
from hiring.services.proctoring_service import proctoring_service
from .forms import *
from .services.gemini_client import GeminiClient
from .services.elevenlabs_client import ElevenLabsClient
from .services.stt import STTClient
import time
import os
import tempfile
import google.generativeai as genai
import uuid
import re
from urllib.parse import quote
from django.utils import timezone







import os
import tempfile
import google.generativeai as genai
import uuid

logger = logging.getLogger(__name__)

# Initialize service clients
gemini_client = GeminiClient()
elevenlabs_client = ElevenLabsClient()
stt_client = STTClient()

# genai.configure(api_key=os.getenv('GEMINI_API_KEY'))


def get_csrf_token(request):
    """Helper function to get CSRF token"""
    from django.middleware.csrf import get_token
    return get_token(request)


def welcome_page(request):
    """Display welcome page for the hiring agent application"""
    return render(request, 'welcome.html')

# =============================================================================
# RECRUITER VIEWS
# =============================================================================

@login_required
def recruiter_dashboard(request):
    """Display the recruiter dashboard with all hiring requests"""
    if not request.user.is_staff and not request.user.is_superuser:
        return redirect('welcome')
    
    hiring_requests = HiringRequest.objects.filter(recruiter=request.user)
    return render(request, 'recruiter/dashboard.html', {
        'hiring_requests': hiring_requests
    })


@login_required
def create_hiring_request(request):
    """Handle creation of new hiring requests and generate assessment questions"""
    if not request.user.is_staff and not request.user.is_superuser:
        return redirect('welcome')
    
    if request.method == 'POST':
        form = HiringRequestForm(request.POST)
        if form.is_valid():
            hiring_request = form.save(commit=False)
            hiring_request.recruiter = request.user
            hiring_request.save()
            
            # Generate questions for both rounds
            generate_round1_questions_for_hiring(hiring_request)
            generate_round2_questions(hiring_request)

            # Create a candidate session automatically
            candidate_session = CandidateSession.objects.create(
                hiring_request=hiring_request
            )
            logger.info(f"Created candidate session with token: {candidate_session.token}")
            
            return redirect('recruiter_dashboard')
    else:
        form = HiringRequestForm()
    
    return render(request, 'recruiter/create_role.html', {'form': form})


@login_required
def view_results(request, request_id):
    """Display candidate results for a specific hiring request with proctoring violations"""
    if not request.user.is_staff and not request.user.is_superuser:
        return redirect('welcome')
    
    hiring_request = get_object_or_404(HiringRequest, id=request_id, recruiter=request.user)
    candidate_sessions = CandidateSession.objects.filter(hiring_request=hiring_request).select_related("evaluationresult")
    
    # Get proctoring violation details for each session
    for session in candidate_sessions:
        session.violations = ProctoringViolation.objects.filter(candidate_session=session)
        session.violation_count = session.violations.count()
        session.camera_violation_count = session.violations.filter(
            violation_type__in=['no_camera', 'camera_off', 'camera_blocked', 'multiple_people', 'person_left', 'extreme_head_turn']
        ).count()
        session.voice_violation_count = session.violations.filter(violation_type='voice_violation').count()
        session.tab_violation_count = session.violations.filter(violation_type__in=['tab_switch', 'tab_resize']).count()
        session.screen_share_violation_count = session.violations.filter(violation_type='screen_share').count()
    
    return render(request, "recruiter/results.html", {
        "hiring_request": hiring_request,
        "candidate_sessions": candidate_sessions,
    })


@login_required
def get_candidate_results(request, request_id):
    """API endpoint to get candidate results in JSON format with enhanced proctoring data"""
    if not request.user.is_staff and not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    hiring_request = get_object_or_404(HiringRequest, id=request_id, recruiter=request.user)
    candidate_sessions = CandidateSession.objects.filter(hiring_request=hiring_request)
    
    results = []
    for session in candidate_sessions:
        try:
            evaluation = EvaluationResult.objects.get(candidate_session=session)
            
            # Get detailed proctoring violations
            violations = ProctoringViolation.objects.filter(candidate_session=session)
            violation_details = [
                {
                    'type': v.violation_type,
                    'severity': v.severity,
                    'timestamp': v.violation_timestamp.isoformat(),
                    'details': v.violation_details,
                    'confidence': v.confidence_score
                } for v in violations
            ]
            
            # Categorize violations
            camera_violations = [v for v in violation_details if any(k in v['type'] for k in ['camera', 'multiple_people', 'person_left', 'extreme_head_turn'])]
            voice_violations = [v for v in violation_details if 'voice' in v['type']]
            tab_violations = [v for v in violation_details if 'tab' in v['type']]
            screen_share_violations = [v for v in violation_details if 'screen_share' in v['type']]
            
            # Status determination with enhanced proctoring categories
            if session.is_terminated:
                status = f"Terminated: {session.termination_reason}"
            elif evaluation.overall_score is not None and evaluation.overall_score >= 0:
                status = "Shortlisted" if evaluation.is_shortlisted else "Not Shortlisted"
            elif session.completed_round2:
                status = "Round 2 Completed"
            elif session.completed_round1:
                status = "Round 1 Completed"
            elif session.current_question_index and session.current_question_index > 0:
                status = "In Progress"
            else:
                status = "Not Started"
                
            results.append({
                'token': str(session.token),
                'email': session.candidate_email or "Not provided",
                'completed_round1': session.completed_round1,
                'completed_round2': session.completed_round2,
                'round1_score': evaluation.round1_score,
                'round2_score': evaluation.round2_score,
                'overall_score': evaluation.overall_score,
                'is_shortlisted': evaluation.is_shortlisted,
                'is_terminated': session.is_terminated,
                'termination_reason': session.termination_reason or "N/A",
                'total_warnings': session.proctoring_warnings_count,
                'camera_warnings': session.camera_warnings_count,
                'voice_warnings': session.voice_warnings_count,
                'tab_warnings': session.tab_warnings_count,
                'screen_share_warnings': session.screen_share_warnings_count,
                'violations': violation_details,
                'camera_violations': camera_violations,
                'voice_violations': voice_violations,
                'tab_violations': tab_violations,
                'screen_share_violations': screen_share_violations,
                'status': status,
                'created_at': session.created_at.isoformat()
            })
        except EvaluationResult.DoesNotExist:
            # Handle case where evaluation doesn't exist yet
            if session.is_terminated:
                status = f"Terminated: {session.termination_reason}"
            else:
                status = "Not Started"
                
            results.append({
                'token': str(session.token),
                'email': session.candidate_email or "Not provided",
                'completed_round1': session.completed_round1,
                'completed_round2': session.completed_round2,
                'round1_score': None,
                'round2_score': None,
                'overall_score': None,
                'is_shortlisted': False,
                'is_terminated': session.is_terminated,
                'termination_reason': session.termination_reason or "N/A",
                'total_warnings': session.proctoring_warnings_count,
                'camera_warnings': session.camera_warnings_count,
                'voice_warnings': session.voice_warnings_count,
                'tab_warnings': session.tab_warnings_count,
                'screen_share_warnings': session.screen_share_warnings_count,
                'violations': [],
                'camera_violations': [],
                'voice_violations': [],
                'tab_violations': [],
                'screen_share_violations': [],
                'status': status,
                'created_at': session.created_at.isoformat()
            })
    
    return JsonResponse({'results': results})


# =============================================================================
# QUESTION GENERATION FUNCTIONS
# =============================================================================

def generate_round1_questions_for_hiring(hiring_request):
    """Generate Round 1 questions for a hiring request and save to database"""
    try:
        logger.info(f"=== GENERATING ROUND 1 QUESTIONS ===")
        logger.info(f"Hiring Request: {hiring_request.work_profile}, {hiring_request.years_experience} years, {hiring_request.difficulty_level}")

        # Generate questions using GeminiClient
        questions_data = gemini_client.generate_questions_with_gemini(
            work_profile=hiring_request.work_profile,
            years_experience=hiring_request.years_experience,
            difficulty_level=hiring_request.difficulty_level,
            number_of_questions_round1=hiring_request.number_of_questions_round1
        )
        
        logger.info(f"=== SAVING {len(questions_data)} QUESTIONS TO DATABASE ===")
        
        saved_count = 0
        for i, q_data in enumerate(questions_data):
            try:
                question_type = q_data.get('question_type', 'mcq')
                logger.info(f"Processing question {i+1}: {question_type}")
                
                question_text = q_data.get('question_text', f'Question {i+1}')
                if not question_text or question_text.strip() == '':
                    question_text = f'Question {i+1}'
                
                model_answer = q_data.get('model_answer', '')
                if not model_answer or model_answer.strip() == '':
                    model_answer = q_data.get('correct_answer', 'Default model answer')
                    if model_answer is None:
                        model_answer = 'Default model answer'
                
                if question_type == 'mcq':
                    correct_answer = q_data.get('correct_answer', 0)
                    
                    try:
                        correct_option_index = int(correct_answer)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid correct_answer for MCQ: {correct_answer}, using default 0")
                        correct_option_index = 0
                    
                    options = q_data.get('options', [])
                    if not options or len(options) == 0:
                        options = ['Option A', 'Option B', 'Option C', 'Option D']
                    
                    if correct_option_index < 0 or correct_option_index >= len(options):
                        correct_option_index = 0
                    
                    Round1Question.objects.create(
                        hiring_request=hiring_request,
                        question_text=question_text,
                        question_type='mcq',
                        options=options,
                        correct_option_index=correct_option_index,
                        model_answer=model_answer
                    )
                else:
                    if not model_answer or model_answer.strip() == '':
                        model_answer = q_data.get('correct_answer', 'Default answer for short answer question')
                    
                    Round1Question.objects.create(
                        hiring_request=hiring_request,
                        question_text=question_text,
                        question_type='short',
                        options=[],
                        correct_option_index=0,
                        model_answer=model_answer
                    )
                
                saved_count += 1
                logger.info(f"✅ Saved question {saved_count}: {question_type}")
                
            except Exception as e:
                logger.error(f"❌ Error saving question {i+1}: {e}")
                continue
        
        logger.info(f"✅ SUCCESS: Saved {saved_count}/{len(questions_data)} questions for hiring request {hiring_request.id}")
        
        if saved_count == 0:
            create_fallback_questions(hiring_request)
            
        return True
        
    except Exception as e:
        logger.error(f"❌ ERROR generating Round 1 questions: {e}")
        create_fallback_questions(hiring_request)
        return False


def create_fallback_questions(hiring_request):
    """Create fallback questions if AI generation fails"""
    try:
        for i in range(hiring_request.number_of_questions_round1):
            if i % 2 == 0:
                Round1Question.objects.create(
                    hiring_request=hiring_request,
                    question_text=f"What is the output of: len('hello')?",
                    question_type="mcq",
                    options=["5", "6", "4", "Error"],
                    correct_option_index=0,
                    model_answer="The len() function returns the number of characters in a string"
                )
            else:
                Round1Question.objects.create(
                    hiring_request=hiring_request,
                    question_text=f"Explain what Python list comprehensions are",
                    question_type="short",
                    model_answer="List comprehensions provide a concise way to create lists based on existing lists or iterables"
                )
        logger.info(f"Created {hiring_request.number_of_questions_round1} fallback questions")
    except Exception as e:
        logger.error(f"Error creating fallback questions: {e}")


def generate_round2_questions(hiring_request):
    """Generate voice interview questions for Round 2 using Gemini AI"""
    try:
        questions_data = gemini_client.generate_voice_interview_questions(
            profile=hiring_request.work_profile,
            years_experience=hiring_request.years_experience,
            difficulty=hiring_request.difficulty_level,
            n=hiring_request.number_of_questions_round2
        )
        
        for i, q_data in enumerate(questions_data):
            Round2Question.objects.create(
                hiring_request=hiring_request,
                question_text=q_data['question'],
                question_order=i + 1,
                model_answer=q_data['model_answer']
            )
        
        logger.info(f"Generated {len(questions_data)} Round 2 questions")
        
    except Exception as e:
        logger.error(f"Error generating Round 2 questions with Gemini: {e}")
        create_fallback_round2_questions(hiring_request)


def create_fallback_round2_questions(hiring_request):
    """Create fallback voice interview questions if AI generation fails"""
    try:
        fallback_questions = [
            {
                "question": f"Describe your most challenging project involving {hiring_request.work_profile} and how you approached it.",
                "model_answer": f"Should discuss specific challenges, technical approach, problem-solving methodology, and lessons learned."
            },
            {
                "question": f"What are the key best practices you follow in {hiring_request.work_profile} development?",
                "model_answer": f"Should mention industry standards, coding practices, testing methodologies, and maintenance strategies."
            },
            {
                "question": f"How do you handle debugging and troubleshooting in {hiring_request.work_profile} environments?",
                "model_answer": f"Should explain systematic debugging approach, tools used, log analysis, and problem-solving techniques."
            },
            {
                "question": f"What recent trends or technologies in {hiring_request.work_profile} are you most excited about and why?",
                "model_answer": f"Should demonstrate awareness of current industry trends, emerging technologies, and their practical applications."
            }
        ]
        
        for i, q_data in enumerate(fallback_questions[:hiring_request.number_of_questions_round2]):
            Round2Question.objects.create(
                hiring_request=hiring_request,
                question_text=q_data['question'],
                question_order=i + 1,
                model_answer=q_data['model_answer']
            )
        
        logger.info(f"Created {hiring_request.number_of_questions_round2} fallback Round 2 questions")
        
    except Exception as e:
        logger.error(f"Error creating fallback Round 2 questions: {e}")


def display_round1_test(request, token):
    """Display Round 1 test page for candidates"""
    try:
        hiring_request = HiringRequest.objects.get(token=token)
        questions = hiring_request.round1_questions.all()
        
        context = {
            'questions': questions,
            'session': {
                'token': token,
                'hiring_request': {
                    'work_profile': hiring_request.work_profile,
                    'difficulty_level': hiring_request.difficulty_level
                }
            }
        }
        
        return render(request, 'round1.html', context)
        
    except HiringRequest.DoesNotExist:
        return render(request, 'error.html', {'message': 'Invalid test session'})
    except Exception as e:
        return render(request, 'error.html', {'message': f'Error loading test: {str(e)}'})
    

# =============================================================================
# CANDIDATE VIEWS
# =============================================================================

def candidate_system_check(request, token):
    """Display system requirements check page before starting the test"""
    session = get_object_or_404(CandidateSession, token=token)
    
    # Prevent access if already completed rounds or terminated
    if session.completed_round1 or session.is_terminated:
        return redirect('candidate_results', token=token)
    
    return render(request, 'candidate/system_check.html', {
        'session': session,
        'token': token
    })


def candidate_round1(request, token):
    """Display Round 1 written assessment for candidates with enhanced proctoring"""
    session = get_object_or_404(CandidateSession, token=token)
    
    # Check system check completion
    try:
        system_check_completed = getattr(session, 'system_check_completed', False)
    except AttributeError:
        system_check_completed = False
    
    # Redirect to system check if not completed
    if not system_check_completed:
        return redirect('candidate_system_check', token=token)

    # Prevent back navigation after completion or termination
    if session.completed_round1 or session.is_terminated:
        return redirect('candidate_results', token=token)
    
    questions = session.hiring_request.round1_questions.all()
    form = Round1AnswerForm(questions=questions)
    
    return render(request, 'candidate/round1.html', {
        'session': session,
        'questions': questions,
        'form': form,
        'token': token
    })


@csrf_exempt
@require_http_methods(["POST"])
def submit_round1(request, token):
    """Handle Round 1 answer submission with enhanced evaluation"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            answers = data.get('answers', {})
            
            logger.info(f"=== ROUND 1 SUBMISSION STARTED ===")
            logger.info(f"Token: {token}")
            logger.info(f"Answers received: {len(answers)}")
            
            session = get_object_or_404(CandidateSession, token=token)
            hiring_request = session.hiring_request
            
            questions = hiring_request.round1_questions.all().order_by('id')
            total_questions = questions.count()
            
            logger.info(f"Total questions in database: {total_questions}")
            
            if total_questions == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'No questions available for evaluation'
                }, status=400)
            
            # Evaluate answers
            total_score = 0
            evaluation_results = []
            
            for question in questions:
                question_id = str(question.id)
                user_answer = answers.get(f'question_{question_id}', '')
                
                logger.info(f"Processing question {question_id}: {question.question_type}")
                
                # Skip if no answer provided
                if not user_answer or user_answer.strip() == '':
                    evaluation_result = {
                        'question_id': question_id,
                        'score': 0.0,
                        'is_correct': False,
                        'user_answer': '',
                        'feedback': 'No answer provided',
                        'correct_answer': question.model_answer
                    }
                    evaluation_results.append(evaluation_result)
                    
                    Round1Answer.objects.update_or_create(
                        candidate_session=session,
                        question=question,
                        defaults={
                            'candidate_answer': '',
                            'score': 0.0,
                            'feedback': 'No answer provided',
                            'is_correct': False
                        }
                    )
                    continue
                
                # Prepare question data for evaluation
                question_data = {
                    'id': question.id,
                    'question_text': question.question_text,
                    'question_type': question.question_type,
                    'options': question.options if question.question_type == 'mcq' else [],
                    'correct_option_index': question.correct_option_index if question.question_type == 'mcq' else 0,
                    'model_answer': question.model_answer
                }
                
                # Use Gemini to evaluate the answer
                evaluation = gemini_client.evaluate_answer(
                    question_data=question_data,
                    candidate_answer=user_answer
                )
                
                question_score = evaluation.get('score', 0.0)
                is_correct = evaluation.get('is_correct', False)
                
                # For MCQ, ensure binary scoring
                if question.question_type == 'mcq':
                    question_score = 1.0 if is_correct else 0.0
                
                total_score += question_score
                
                evaluation_result = {
                    'question_id': question_id,
                    'score': question_score,
                    'is_correct': is_correct,
                    'user_answer': user_answer,
                    'feedback': evaluation.get('explanation', ''),
                    'correct_answer': evaluation.get('correct_answer', question.model_answer),
                    'confidence': evaluation.get('confidence', 0)
                }
                evaluation_results.append(evaluation_result)
                
                Round1Answer.objects.update_or_create(
                    candidate_session=session,
                    question=question,
                    defaults={
                        'candidate_answer': user_answer,
                        'score': question_score,
                        'feedback': evaluation.get('explanation', ''),
                        'is_correct': is_correct
                    }
                )
                
                time.sleep(0.5)
            
            # Calculate percentage
            percentage = (total_score / total_questions) * 100 if total_questions > 0 else 0
            
            # Determine if candidate passes (60% threshold)
            passed = percentage >= 60
            
            # Save results to session
            session.completed_round1 = True
            session.save()
            
            # Create or update evaluation result
            eval_result, created = EvaluationResult.objects.get_or_create(
                candidate_session=session
            )
            eval_result.round1_score = percentage
            eval_result.overall_score = percentage
            eval_result.is_shortlisted = passed
            eval_result.save()
            
            logger.info(f"=== ROUND 1 SUBMISSION COMPLETED ===")
            logger.info(f"Total Score: {total_score}/{total_questions}")
            logger.info(f"Percentage: {percentage}%")
            logger.info(f"Passed: {passed}")
            
            return JsonResponse({
                'success': True,
                'passed': passed,
                'score': round(total_score, 2),
                'total_questions': total_questions,
                'percentage': round(percentage, 2),
                'evaluation_results': evaluation_results
            })
            
        except Exception as e:
            logger.error(f"Error submitting Round 1 answers: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return JsonResponse({
                'success': False,
                'error': f'Submission error: {str(e)}'
            }, status=500)


def candidate_round2(request, token):
    """Display Round 2 voice interview interface with enhanced proctoring"""
    session = get_object_or_404(CandidateSession, token=token)
    
    # Prevent access if not eligible or already completed
    if not session.completed_round1 or session.completed_round2 or session.is_terminated:
        return redirect('candidate_results', token=token)
    
    # Get current question progress
    current_question_index = session.current_question_index or 0
    questions = session.hiring_request.round2_questions.all().order_by('question_order')
    
    # Redirect to results if all questions answered
    if current_question_index >= questions.count():
        session.completed_round2 = True
        session.save()
        return redirect('candidate_results', token=token)
    
    current_question = questions[current_question_index]
    
    # Calculate progress percentage
    progress_percentage = (current_question_index / questions.count()) * 100
    
    return render(request, 'candidate/round2.html', {
        'session': session,
        'current_question': current_question,
        'current_question_index': current_question_index + 1,
        'total_questions': questions.count(),
        'progress_percentage': progress_percentage,
        'token': token
    })


def candidate_results(request, token):
    """Display candidate results after completing rounds"""
    session = get_object_or_404(CandidateSession, token=token)
    
    try:
        evaluation = EvaluationResult.objects.get(candidate_session=session)
    except EvaluationResult.DoesNotExist:
        evaluation = None
    
    # Get violation summary
    violations = ProctoringViolation.objects.filter(candidate_session=session)
    
    return render(request, 'candidate/results.html', {
        'session': session,
        'evaluation': evaluation,
        'violations': violations,
        'violation_count': violations.count()
    })


def terminated_view(request):
    """Handle test termination due to proctoring violations"""
    token = request.GET.get("token")
    
    try:
        session = CandidateSession.objects.get(token=token)

        # Mark session as terminated if not already
        if not session.is_terminated:
            session.is_terminated = True
            if not session.termination_reason or session.termination_reason == "N/A":
                session.termination_reason = "Test terminated due to proctoring violations"
            session.completed_round1 = False
            session.completed_round2 = False
            session.current_question_index = 0
            session.save()

            # Update evaluation result
            eval_result, created = EvaluationResult.objects.get_or_create(candidate_session=session)
            eval_result.round1_score = None
            eval_result.round2_score = None  
            eval_result.overall_score = None
            eval_result.is_shortlisted = False
            eval_result.save()

        logger.info(f"Session {token} terminated: {session.termination_reason}")

        # Return JSON for AJAX calls
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'message': 'Test terminated successfully',
                'redirect_url': f'/terminated/?token={token}'
            })
            
    except CandidateSession.DoesNotExist:
        logger.error(f"Termination attempted for non-existent session token: {token}")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Session not found'}, status=404)

    return render(request, "candidate/terminated.html", {'token': token})


# =============================================================================
# AUDIO SUBMISSION
# =============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def submit_audio_answer(request, token):
    """Handle audio answer submission with transcription and AI evaluation"""
    logger.info(f"Audio submission request for token: {token}")
    
    try:
        session = get_object_or_404(CandidateSession, token=token)
        question_id = request.POST.get('question_id')
        
        if not question_id:
            return JsonResponse({'error': 'Question ID required'}, status=400)
        
        question = get_object_or_404(Round2Question, id=question_id, hiring_request=session.hiring_request)
        
        if 'audio' not in request.FILES:
            return JsonResponse({'error': 'No audio file provided'}, status=400)
        
        audio_file = request.FILES['audio']
        logger.info(f"Audio file received: {audio_file.name}, size: {audio_file.size} bytes")
        
        if audio_file.size > 10 * 1024 * 1024:
            return JsonResponse({'error': 'File too large. Maximum 10MB allowed.'}, status=400)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_audio:
            for chunk in audio_file.chunks():
                temp_audio.write(chunk)
            temp_audio_path = temp_audio.name
        
        try:
            # Step 1: Transcribe audio
            transcription_result = stt_client.transcribe_audio(temp_audio_path)
            logger.info(f"Transcription completed: {transcription_result.get('success', False)}")
            
            transcribed_text = transcription_result.get('text', '')
            if not transcribed_text or len(transcribed_text.strip()) < 5:
                transcribed_text = "Audio could not be transcribed clearly."
            
            logger.info(f"Transcribed text: {transcribed_text[:100]}...")
            
            # Step 2: Evaluate answer using Gemini AI
            evaluation = gemini_client.evaluate_voice_answer(
                question_text=question.question_text,
                model_answer=question.model_answer,
                candidate_answer=transcribed_text,
                difficulty_level=session.hiring_request.difficulty_level,
                work_profile=session.hiring_request.work_profile,
                years_experience=session.hiring_request.years_experience
            )
            
            logger.info(f"Evaluation completed: score={evaluation.get('score', 0)}")
            
            # Step 3: Save audio file
            timestamp = int(time.time())
            file_name = f"answer_{session.token}_{question_id}_{timestamp}.webm"
            file_path = default_storage.save(f'audio/{file_name}', audio_file)
            
            # Step 4: Convert score to percentage
            score_percentage = evaluation.get('score', 0) * 100
            
            round2_answer = Round2Answer(
                candidate_session=session,
                question=question,
                audio_response_path=file_path,
                transcribed_text=transcribed_text,
                score=score_percentage,
                feedback=evaluation.get('explanation', ''),
                keywords_matched=evaluation.get('keywords_matched', []),
                improvement_suggestions=evaluation.get('improvement_suggestions', []),
                evaluation_confidence=evaluation.get('confidence', 0.0)
            )
            round2_answer.save()
            
            # Step 5: Update session progress
            current_index = session.current_question_index or 0
            session.current_question_index = current_index + 1
            
            total_questions = session.hiring_request.round2_questions.count()
            answered_count = session.round2_answers.count()
            completed = answered_count >= total_questions
            
            overall_score = 0
            is_shortlisted = False
            
            if completed:
                session.completed_round2 = True
                
                # Calculate final score
                total_score = sum(answer.score for answer in session.round2_answers.all())
                average_score = (total_score / total_questions) if total_questions > 0 else 0
                
                # Update evaluation result
                eval_result, created = EvaluationResult.objects.get_or_create(candidate_session=session)
                eval_result.round2_score = average_score
                
                round1_score = eval_result.round1_score or 0
                if round1_score > 0:
                    eval_result.overall_score = (round1_score + average_score) / 2
                else:
                    eval_result.overall_score = average_score
                    
                eval_result.is_shortlisted = eval_result.overall_score >= 60
                eval_result.save()
                
                overall_score = eval_result.overall_score
                is_shortlisted = eval_result.is_shortlisted
            
            session.save()
            
            response_data = {
                'success': True,
                'transcription': transcribed_text,
                'score': round(score_percentage, 2),
                'feedback': evaluation.get('explanation', ''),
                'is_correct': evaluation.get('is_correct', False),
                'keywords_matched': evaluation.get('keywords_matched', []),
                'completed': completed,
                'progress': f"{answered_count}/{total_questions}",
                'current_question_index': session.current_question_index,
            }
            
            if completed:
                response_data['is_shortlisted'] = is_shortlisted
                response_data['overall_score'] = round(overall_score, 2)
                response_data['redirect_url'] = f'/candidate/{token}/results/'
            
            logger.info(f"Audio answer processed successfully")
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Error processing audio answer: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Audio processing error: {str(e)}'
            }, status=500)
            
        finally:
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
        
    except Exception as e:
        logger.error(f"Error in audio submission endpoint: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_complete_system_check(request, token):
    """API endpoint to mark system check as completed"""
    try:
        session = get_object_or_404(CandidateSession, token=token)
        session.system_check_completed = True
        session.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def validate_system_requirements(request):
    """Enhanced system validation with accurate screen sharing detection"""
    try:
        data = json.loads(request.body)
        
        # Detect screen sharing
        screen_sharing_result = screen_sharing_detector.detect_screen_sharing()
        
        # Extract detected apps from processes (for compatibility)
        detected_apps = []
        for process in screen_sharing_result.get('detected_processes', []):
            if process.get('category') != 'browser_sharing':  # Exclude browsers from apps list
                detected_apps.append({
                    'name': process.get('name', 'unknown'),
                    'pid': process.get('pid'),
                    'category': process.get('category', 'unknown')
                })
        
        # Extract browser tabs/instances
        browser_issues = screen_sharing_result.get('browser_issues', {})
        detected_browser_tabs = []
        for instance in browser_issues.get('detected_instances', []):
            service = instance.get('service', 'unknown')
            detected_browser_tabs.append(service)
        
        # Also check processes marked as browser_sharing
        for process in screen_sharing_result.get('detected_processes', []):
            if process.get('category') == 'browser_sharing':
                service = process.get('service', 'browser_sharing')
                if service not in detected_browser_tabs:
                    detected_browser_tabs.append(service)
        
        validation_result = {
            'is_sharing': screen_sharing_result['is_sharing'],
            'detected_apps': detected_apps,
            'detected_browser_tabs': detected_browser_tabs,
            'detected_processes': screen_sharing_result.get('detected_processes', []),
            'display_issues': screen_sharing_result.get('display_issues', {}),
            'active_sharing_detected': screen_sharing_result['is_sharing'],
            'total_detections': screen_sharing_result['total_detections'],
            'confidence': screen_sharing_result['confidence'],
            'can_proceed': screen_sharing_result['can_proceed'],
            'severity': screen_sharing_result.get('severity', 'none'),
            'reasons': screen_sharing_result.get('reasons', [])
        }
        
        logger.info(f"System validation: can_proceed={validation_result['can_proceed']}, detections={validation_result['total_detections']}")
        
        return JsonResponse(validation_result)
        
    except Exception as e:
        logger.error(f"System validation error: {e}", exc_info=True)
        return JsonResponse({
            'error': str(e),
            'can_proceed': False,
            'is_sharing': True
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def enhanced_validate_system(request):
    """Enhanced system validation with comprehensive checks"""
    try:
        # Perform screen sharing detection
        screen_sharing_result = screen_sharing_detector.detect_screen_sharing()
        
        return JsonResponse(screen_sharing_result)
        
    except Exception as e:
        logger.error(f"Enhanced validation error: {e}")
        return JsonResponse({
            'error': str(e),
            'can_proceed': False,
            'is_sharing': True
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_terminate_test(request):
    """API endpoint to terminate test session"""
    try:
        data = json.loads(request.body)
        token = data.get('token')
        reason = data.get('reason', 'Proctoring violation detected')
        
        if not token:
            return JsonResponse({'error': 'Token is required'}, status=400)
            
        session = CandidateSession.objects.get(token=token)
        
        session.is_terminated = True
        session.termination_reason = reason
        session.completed_round1 = False
        session.completed_round2 = False
        session.current_question_index = 0
        session.save()

        # Update evaluation result
        eval_result, created = EvaluationResult.objects.get_or_create(candidate_session=session)
        eval_result.round1_score = None
        eval_result.round2_score = None  
        eval_result.overall_score = None
        eval_result.is_shortlisted = False
        eval_result.save()

        logger.info(f"Session {token} terminated via API: {reason}")
        
        return JsonResponse({
            'success': True, 
            'message': 'Test terminated successfully',
            'redirect_url': f'/terminated/?token={token}'
        })
        
    except CandidateSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in termination API: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_generate_questions(request):
    """API endpoint to generate questions using Gemini AI"""
    try:
        data = json.loads(request.body)
        questions = gemini_client.generate_questions(
            profile=data.get('profile', ''),
            years_experience=data.get('years_experience', 0),
            difficulty=data.get('difficulty', 'intermediate'),
            n=data.get('n', 5)
        )
        return JsonResponse({'questions': questions})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_evaluate_answer(request):
    """API endpoint to evaluate answers using Gemini AI"""
    try:
        data = json.loads(request.body)
        
        question_data = {
            'type': data.get('type', 'short'),
            'question': data.get('question', ''),
            'model_answer': data.get('rubric', ''),
            'options': data.get('options', []),
            'correct_option_index': data.get('correct_option_index', 0)
        }
        
        evaluation = gemini_client.evaluate_answer(
            question_data=question_data,
            candidate_answer=data.get('answer', '')
        )
        return JsonResponse(evaluation)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_synthesize_speech(request):
    """API endpoint for text-to-speech synthesis"""
    try:
        data = json.loads(request.body)
        text = data.get('text', 'Test question')
        
        logger.info(f"TTS request for text: {text[:50]}...")
        
        audio_path = elevenlabs_client.synthesize_text_to_audio(text)
        
        if audio_path and os.path.exists(audio_path):
            filename = os.path.basename(audio_path)
            media_url = f"/media/audio/{filename}"
            
            return JsonResponse({
                'audio_url': media_url,
                'file_path': audio_path,
                'status': 'success'
            })
        else:
            return JsonResponse({
                'audio_url': '/static/audio/sample.mp3',
                'status': 'fallback'
            })
            
    except Exception as e:
        logger.error(f"Error in TTS endpoint: {e}")
        return JsonResponse({
            'audio_url': '/static/audio/sample.mp3',
            'error': str(e),
            'status': 'error_fallback'
        }, status=500)
    
# =============================================================================
# ENHANCED PROCTORING API ENDPOINTS
# =============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_initialize_proctoring(request, token):
    """Initialize enhanced proctoring for a candidate session"""
    try:
        session = get_object_or_404(CandidateSession, token=token)
        
        session.camera_enabled = True
        session.audio_enabled = True
        session.is_proctoring_active = True
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Enhanced proctoring initialized successfully',
            'max_warnings': 3,
            'current_warnings': session.proctoring_warnings_count,
            'camera_warnings': session.camera_warnings_count,
            'voice_warnings': session.voice_warnings_count,
            'tab_warnings': session.tab_warnings_count,
            'screen_share_warnings': session.screen_share_warnings_count
        })
        
    except Exception as e:
        logger.error(f"Error initializing proctoring: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


from .services.proctoring_service import proctoring_service

@csrf_exempt
@require_http_methods(["POST"])
def api_process_proctoring_frame(request, token):
    """
    Enhanced API endpoint to process camera frames with comprehensive violation detection
    """
    try:
        session = get_object_or_404(CandidateSession, token=token)
        
        # Check if session is terminated
        if session.is_terminated:
            return JsonResponse({
                'success': False,
                'error': 'Session already terminated',
                'terminated': True,
                'termination_reason': session.termination_reason
            })
        
        try:
            body = request.body.decode('utf-8') if isinstance(request.body, bytes) else request.body
            data = json.loads(body) if body else {}
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Invalid request body in process-frame: {e}")
            return JsonResponse({'success': False, 'error': 'Invalid request body'}, status=400)
        
        image_data = data.get('image_data')
        head_turn_duration_exceeded = data.get('head_turn_duration_exceeded', False)
        person_left_5s_exceeded = data.get('person_left_5s_exceeded', False)
        
        if not image_data:
            return JsonResponse({'success': False, 'error': 'No image data provided'})
        
        # Process camera frame using enhanced MediaPipe service
        analysis_results = proctoring_service.process_camera_frame(image_data, str(token))
        
        if 'error' in analysis_results:
            return JsonResponse({
                'success': False, 
                'error': analysis_results['error']
            })
        
        violations_detected = []
        screenshot_path = analysis_results.get('screenshot_path')
        
        # Face absent >5s: terminate immediately (client sends person_left_5s_exceeded after 5s no face)
        if person_left_5s_exceeded:
            session.add_proctoring_violation(
                violation_type='person_left',
                details='Face not visible in camera feed for more than 5 seconds',
                screenshot_path=screenshot_path,
                severity='warning'
            )
            session.is_terminated = True
            session.termination_reason = 'Test terminated: Face not visible for more than 5 seconds'
            session.save()
            session.refresh_from_db()
            violations_detected.append({
                'type': 'person_left',
                'message': 'Face not visible for more than 5 seconds',
                'severity': 'critical',
                'confidence': 0.9,
                'warning_count': session.proctoring_warnings_count
            })
        
        # Head turn ~90° continuous >5s: one warning per occurrence; max 2 warnings, 3rd = terminate (handled in model)
        if head_turn_duration_exceeded:
            warning_count = session.add_proctoring_violation(
                violation_type='extreme_head_turn',
                details='Looking left or right (head turn) continuously for more than 5 seconds',
                screenshot_path=screenshot_path,
                severity='warning'
            )
            session.refresh_from_db()
            violations_detected.append({
                'type': 'extreme_head_turn',
                'message': 'Looking away from screen (head turn) for more than 5 seconds',
                'severity': 'warning',
                'confidence': 0.8,
                'warning_count': warning_count
            })
        
        # Process violations from analysis (skip person_left and extreme_head_turn - handled by client flags above)
        # ✅ FIX: Only record HIGH-CONFIDENCE violations to prevent false positives
        VIOLATION_CONFIDENCE_THRESHOLD = 0.9  # 90% confidence required
        skip_types = {'person_left', 'extreme_head_turn'}
        for violation in analysis_results.get('violations', []):
            violation_type = violation['type']
            if violation_type in skip_types:
                continue
            
            # ✅ FIX: Filter by confidence - skip low-confidence detections
            confidence = violation.get('confidence', 0.0)
            if confidence < VIOLATION_CONFIDENCE_THRESHOLD:
                logger.info(f"Skipping low-confidence violation: {violation_type} (confidence: {confidence:.2f})")
                continue
            
            violation_message = violation['message']
            severity = violation.get('severity', 'warning')
            warning_count = session.add_proctoring_violation(
                violation_type=violation_type,
                details=violation_message,
                screenshot_path=screenshot_path,
                severity=severity
            )
            violations_detected.append({
                'type': violation_type,
                'message': violation_message,
                'severity': severity,
                'confidence': confidence,
                'warning_count': warning_count
            })
        
        session.refresh_from_db()
        
        # Ensure all response values are JSON-serializable (no numpy types)
        def _to_native(val):
            if hasattr(val, 'item'):  # numpy scalar
                return val.item()
            if isinstance(val, (dict,)):
                return {k: _to_native(v) for k, v in val.items()}
            if isinstance(val, (list,)):
                return [_to_native(v) for v in val]
            return val
        
        confidence_scores = analysis_results.get('confidence_scores', {}) or {}
        head_yaw = analysis_results.get('head_yaw_degrees', 0)
        
        response_data = {
            'success': True,
            'face_detected': bool(analysis_results.get('face_detected', False)),
            'face_count': int(analysis_results.get('face_count', 0)),
            'multiple_people_detected': bool(analysis_results.get('multiple_people_detected', False)),
            'person_left': bool(analysis_results.get('person_left', True)),
            'camera_blocked': bool(analysis_results.get('camera_blocked', False)),
            'camera_off': bool(analysis_results.get('camera_off', False)),
            'extreme_head_turn': bool(analysis_results.get('extreme_head_turn', False)),
            'head_yaw_degrees': float(head_yaw) if head_yaw is not None else 0.0,
            'looking_away': bool(analysis_results.get('looking_away', False)),
            'mobile_phone_detected': bool(analysis_results.get('mobile_phone_detected', False)),
            'electronic_device_detected': bool(analysis_results.get('electronic_device_detected', False)),
            'face_occluded': bool(analysis_results.get('face_occluded', False)),
            'natural_behavior_detected': bool(analysis_results.get('natural_behavior_detected', False)),
            'violations_detected': violations_detected,
            'total_warnings': int(session.proctoring_warnings_count),
            'current_warning_count': int(session.proctoring_warnings_count),
            'camera_warnings': int(session.camera_warnings_count),
            'voice_warnings': int(session.voice_warnings_count),
            'tab_warnings': int(session.tab_warnings_count),
            'screen_share_warnings': int(session.screen_share_warnings_count),
            'is_terminated': bool(session.is_terminated),
            'confidence_scores': _to_native(confidence_scores)
        }
        
        if session.is_terminated:
            response_data['redirect_url'] = f'/terminated/?token={token}&reason={session.termination_reason}'
            response_data['termination_reason'] = str(session.termination_reason or '')
        
        return JsonResponse(_to_native(response_data))
        
    except Exception as e:
        import traceback
        logger.error(f"Error processing proctoring frame: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'Proctoring error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_force_terminate_sharing(request, token):
    """API endpoint to force terminate screen sharing applications"""
    try:
        session = get_object_or_404(CandidateSession, token=token)
        
        # Force terminate detected sharing applications
        termination_result = screen_sharing_detector.force_terminate_sharing_apps()
        
        # Re-check screen sharing status
        screen_sharing_result = screen_sharing_detector.detect_screen_sharing()
        
        # Build response message
        message_parts = []
        if termination_result.get('successful'):
            message_parts.append(f"Terminated {len(termination_result['successful'])} screen sharing app(s)")
        if termination_result.get('browser_warnings'):
            browser_msg = f"Detected {len(termination_result['browser_warnings'])} browser(s) with screen sharing. Please close the sharing tab manually."
            message_parts.append(browser_msg)
        if termination_result.get('failed'):
            message_parts.append(f"Could not terminate {len(termination_result['failed'])} process(es)")
        
        message = ". ".join(message_parts) if message_parts else termination_result.get('details', 'No processes to terminate')
        
        return JsonResponse({
            'success': len(termination_result.get('successful', [])) > 0,
            'terminated_apps': [app['name'] for app in termination_result.get('successful', [])],
            'browser_warnings': termination_result.get('browser_warnings', []),
            'failed': termination_result.get('failed', []),
            'screen_sharing_still_detected': screen_sharing_result['is_sharing'],
            'message': message,
            'details': termination_result.get('details', '')
        })
        
    except Exception as e:
        logger.error(f"Error force terminating sharing apps: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_process_voice_sample(request, token):
    """
    API endpoint to process voice samples for multiple voice detection
    """
    try:
        session = get_object_or_404(CandidateSession, token=token)
        
        if session.is_terminated:
            return JsonResponse({
                'success': False,
                'error': 'Session already terminated',
                'terminated': True
            })
        
        data = json.loads(request.body)
        multiple_voices_detected = data.get('multiple_voices_detected', False)
        voice_count = data.get('voice_count', 1)
        confidence = data.get('confidence', 0.0)
        
        if multiple_voices_detected and voice_count > 1:
            warning_count = session.add_proctoring_violation(
                violation_type='voice_violation',
                details=f"Multiple voices detected: {voice_count} voices, confidence: {confidence}",
                severity='critical'
            )
            
            return JsonResponse({
                'success': True,
                'violation_detected': True,
                'voice_count': voice_count,
                'confidence': confidence,
                'warning_count': warning_count,
                'total_warnings': session.proctoring_warnings_count,
                'is_terminated': session.is_terminated
            })
        
        return JsonResponse({
            'success': True,
            'violation_detected': False,
            'voice_count': voice_count,
            'confidence': confidence
        })
        
    except Exception as e:
        logger.error(f"Error processing voice sample: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_track_tab_event(request, token):
    """
    API endpoint to track tab events
    """
    try:
        session = get_object_or_404(CandidateSession, token=token)
        
        if session.is_terminated:
            return JsonResponse({
                'success': False,
                'error': 'Session already terminated',
                'terminated': True
            })
        
        data = json.loads(request.body)
        event_type = data.get('event_type')
        event_details = data.get('details', '')
        
        violation_type_map = {
            'tab_switch': 'tab_switch',
            'tab_resize': 'tab_resize',
            'visibility_change': 'tab_switch'
        }
        
        violation_type = violation_type_map.get(event_type, 'tab_switch')
        
        warning_count = session.add_proctoring_violation(
            violation_type=violation_type,
            details=f"Tab event: {event_type} - {event_details}",
            severity='warning'
        )
        
        return JsonResponse({
            'success': True,
            'violation_recorded': True,
            'event_type': event_type,
            'warning_count': warning_count,
            'total_warnings': session.proctoring_warnings_count,
            'tab_warnings': session.tab_warnings_count,
            'is_terminated': session.is_terminated
        })
        
    except Exception as e:
        logger.error(f"Error tracking tab event: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_check_screen_sharing_during_test(request, token):
    """
    API endpoint to check for screen sharing during test
    """
    try:
        session = get_object_or_404(CandidateSession, token=token)
        
        if session.is_terminated:
            return JsonResponse({
                'success': False,
                'error': 'Session already terminated',
                'terminated': True
            })
        
        screen_sharing_result = screen_sharing_detector.detect_screen_sharing()
        
        if screen_sharing_result.get('is_sharing', False):
            # Safely get detected apps and browser tabs with defaults
            detected_apps = screen_sharing_result.get('detected_apps', [])
            
            # Extract browser tabs from browser_issues if available
            detected_browser_tabs = []
            browser_issues = screen_sharing_result.get('browser_issues', {})
            if browser_issues and 'detected_instances' in browser_issues:
                detected_browser_tabs = [instance.get('service', instance.get('browser', 'Unknown')) 
                                       for instance in browser_issues['detected_instances']]
            
            # Also check detected_processes for browser-based sharing
            detected_processes = screen_sharing_result.get('detected_processes', [])
            for process in detected_processes:
                if process.get('is_browser') and process.get('service'):
                    service = process.get('service')
                    if service not in detected_browser_tabs:
                        detected_browser_tabs.append(service)
            
            # ✅ FIX: Do NOT record violation here - this is just a detection check
            # The frontend will call this API periodically to CHECK status
            # Violation recording happens in frontend when screen sharing is CONFIRMED
            # Commented out automatic violation recording to prevent false positives
            
            # # Build violation details safely
            # apps_list = []
            # if detected_apps:
            #     apps_list = [app.get('display_name', app.get('name', str(app))) if isinstance(app, dict) else str(app) for app in detected_apps]
            # 
            # apps_detected = ', '.join(apps_list) if apps_list else 'Unknown apps'
            # tabs_detected = ', '.join(detected_browser_tabs) if detected_browser_tabs else 'No browser tabs detected'
            # 
            # violation_details = f"Screen sharing detected - Apps: {apps_detected}, Tabs: {tabs_detected}"
            # 
            # warning_count = session.add_proctoring_violation(
            #     violation_type='screen_share',
            #     details=violation_details,
            #     severity='critical'
            # )
            
            return JsonResponse({
                'success': True,
                'is_sharing': True,
                'detected_apps': detected_apps,
                'detected_browser_tabs': detected_browser_tabs,
                # Return current session state without modifying it
                'total_warnings': session.proctoring_warnings_count,
                'is_terminated': session.is_terminated
            })
        
        return JsonResponse({
            'success': True,
            'is_sharing': False
        })

        
    except Exception as e:
        logger.error(f"Error checking screen sharing: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_record_violation(request, token):
    """
    Record browser violations (tab switch, right-click, etc.) - no camera image needed.
    Returns current_warning_count so frontend can update the displayed count immediately.
    """
    try:
        session = get_object_or_404(CandidateSession, token=token)
        if session.is_terminated:
            reason = quote(str(session.termination_reason or "Terminated"))
            return JsonResponse({
                'success': True,
                'error': 'Session already terminated',
                'terminated': True,
                'current_warning_count': session.proctoring_warnings_count,
                'is_terminated': True,
                'redirect_url': f'/terminated/?token={token}&reason={reason}'
            })
        data = json.loads(request.body)
        violation_type = data.get('violation_type', 'tab_switch')
        details = data.get('details', violation_type)
        # Normalize tab-related types for correct counter (model checks "tab" in type)
        if violation_type in ('tab_hidden', 'tab_app_switch', 'visibility_change'):
            violation_type = 'tab_switch'
        session.add_proctoring_violation(
            violation_type=violation_type,
            details=details,
            severity='warning'
        )
        session.refresh_from_db()
        result = {
            'success': True,
            'current_warning_count': session.proctoring_warnings_count,
            'total_warnings': session.proctoring_warnings_count,
            'is_terminated': session.is_terminated
        }
        if session.is_terminated:
            reason = quote(str(session.termination_reason or "Terminated"))
            result['redirect_url'] = f'/terminated/?token={token}&reason={reason}'
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error recording violation: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_mark_screen_sharing_detected(request, token):
    """API endpoint to mark screen sharing as detected"""
    try:
        session = get_object_or_404(CandidateSession, token=token)
        session.mark_screen_sharing_detected()
        
        return JsonResponse({
            'success': True,
            'message': 'Screen sharing marked as detected',
            'screen_sharing_blocked': True
        })
        
    except Exception as e:
        logger.error(f"Error marking screen sharing detected: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_mark_screen_sharing_resolved(request, token):
    """API endpoint to mark screen sharing as resolved"""
    try:
        session = get_object_or_404(CandidateSession, token=token)
        session.mark_screen_sharing_resolved()
        
        return JsonResponse({
            'success': True,
            'message': 'Screen sharing marked as resolved',
            'screen_sharing_blocked': False
        })
        
    except Exception as e:
        logger.error(f"Error marking screen sharing resolved: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

        