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
import os
import tempfile

logger = logging.getLogger(__name__)

# Initialize service clients
gemini_client = GeminiClient()
elevenlabs_client = ElevenLabsClient()
stt_client = STTClient()

# =============================================================================
# RECRUITER VIEWS
# =============================================================================

@login_required
def recruiter_dashboard(request):
    """
    Display the recruiter dashboard with all hiring requests.
    """
    hiring_requests = HiringRequest.objects.filter(recruiter=request.user)
    return render(request, 'recruiter/dashboard.html', {
        'hiring_requests': hiring_requests
    })

@login_required
def create_hiring_request(request):
    """
    Handle creation of new hiring requests and generate assessment questions.
    """
    if request.method == 'POST':
        form = HiringRequestForm(request.POST)
        if form.is_valid():
            hiring_request = form.save(commit=False)
            hiring_request.recruiter = request.user
            hiring_request.save()
            
            # Generate questions for both rounds
            generate_round1_questions(hiring_request)
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

def generate_round1_questions(hiring_request):
    """
    Generate written assessment questions for Round 1 using Gemini AI.
    """
    try:
        questions_data = gemini_client.generate_questions(
            profile=hiring_request.work_profile,
            years_experience=hiring_request.years_experience,
            difficulty=hiring_request.difficulty_level,
            n=hiring_request.number_of_questions_round1
        )
        
        for q_data in questions_data:
            Round1Question.objects.create(
                hiring_request=hiring_request,
                question_text=q_data['question'],
                question_type=q_data['type'],
                options=q_data.get('options'),
                correct_option_index=q_data.get('correct_option_index'),
                model_answer=q_data['model_answer']
            )
        
        logger.info(f"Generated {len(questions_data)} questions for hiring request {hiring_request.id}")
        
    except Exception as e:
        logger.error(f"Error generating Round 1 questions: {e}")
        create_fallback_questions(hiring_request)

def create_fallback_questions(hiring_request):
    """
    Create fallback questions if AI generation fails.
    """
    try:
        for i in range(hiring_request.number_of_questions_round1):
            if i % 2 == 0:
                # Multiple choice questions
                Round1Question.objects.create(
                    hiring_request=hiring_request,
                    question_text=f"Question {i+1}: What is important for {hiring_request.work_profile}?",
                    question_type="mcq",
                    options=["Option A", "Option B", "Option C", "Option D"],
                    correct_option_index=0,
                    model_answer="Expected answer for this question"
                )
            else:
                # Short answer questions
                Round1Question.objects.create(
                    hiring_request=hiring_request,
                    question_text=f"Question {i+1}: Describe your approach to {hiring_request.work_profile}",
                    question_type="short",
                    model_answer="Expected detailed answer"
                )
        logger.info(f"Created {hiring_request.number_of_questions_round1} fallback questions")
    except Exception as e:
        logger.error(f"Error creating fallback questions: {e}")

def generate_round2_questions(hiring_request):
    """
    Generate voice interview questions for Round 2 using Gemini AI.
    """
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
        
        logger.info(f"Generated {len(questions_data)} dynamic Round 2 questions for {hiring_request.work_profile}")
        
    except Exception as e:
        logger.error(f"Error generating Round 2 questions with Gemini: {e}")
        create_fallback_round2_questions(hiring_request)

def create_fallback_round2_questions(hiring_request):
    """
    Create fallback voice interview questions if AI generation fails.
    """
    try:
        fallback_questions = [
            {
                "question": f"Describe your most challenging project involving {hiring_request.work_profile} and how you approached it.",
                "model_answer": f"Should discuss specific challenges, technical approach, problem-solving methodology, and lessons learned related to {hiring_request.work_profile}."
            },
            {
                "question": f"What are the key best practices you follow in {hiring_request.work_profile} development?",
                "model_answer": f"Should mention industry standards, coding practices, testing methodologies, and maintenance strategies for {hiring_request.work_profile}."
            },
            {
                "question": f"How do you handle debugging and troubleshooting in {hiring_request.work_profile} environments?",
                "model_answer": f"Should explain systematic debugging approach, tools used, log analysis, and problem-solving techniques specific to {hiring_request.work_profile}."
            },
            {
                "question": f"What recent trends or technologies in {hiring_request.work_profile} are you most excited about and why?",
                "model_answer": f"Should demonstrate awareness of current industry trends, emerging technologies, and their practical applications in {hiring_request.work_profile}."
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

# =============================================================================
# CANDIDATE VIEWS
# =============================================================================

def candidate_round1(request, token):
    """
    Display Round 1 written assessment for candidates.
    """
    session = get_object_or_404(CandidateSession, token=token)
    
    if session.completed_round1:
        return redirect('candidate_results', token=token)
    
    questions = session.hiring_request.round1_questions.all()
    form = Round1AnswerForm(questions=questions)
    
    return render(request, 'candidate/round1.html', {
        'session': session,
        'questions': questions,
        'form': form
    })

@csrf_exempt
@require_http_methods(["POST"])
def submit_round1(request, token):
    """
    Handle submission and evaluation of Round 1 answers.
    """
    session = get_object_or_404(CandidateSession, token=token)
    
    if session.completed_round1:
        return JsonResponse({'error': 'Round 1 already completed'}, status=400)
    
    try:
        data = json.loads(request.body)
        answers = data.get('answers', {})
        
        total_score = 0
        total_questions = session.hiring_request.round1_questions.count()
        
        for question_id, candidate_answer in answers.items():
            try:
                question = get_object_or_404(Round1Question, id=int(question_id), hiring_request=session.hiring_request)
            except (ValueError, TypeError):
                continue  # Skip invalid question IDs
            
            # Evaluate answer using Gemini AI
            evaluation = gemini_client.evaluate_answer(
                question_rubric=question.model_answer,
                candidate_answer=candidate_answer,
                question_type=question.question_type
            )
            
            # Save answer with evaluation results
            round1_answer = Round1Answer(
                candidate_session=session,
                question=question,
                candidate_answer=candidate_answer,
                score=evaluation.get('score', 0),
                feedback=evaluation.get('explanation', '')
            )
            round1_answer.save()
            
            total_score += evaluation.get('score', 0)
        
        # Calculate percentage score
        score_percentage = (total_score / total_questions) * 100 if total_questions > 0 else 0
        
        # Update session status
        session.completed_round1 = True
        session.save()
        
        # Create or update evaluation result
        eval_result, created = EvaluationResult.objects.get_or_create(candidate_session=session)
        eval_result.round1_score = score_percentage
        eval_result.save()
        
        return JsonResponse({
            'success': True,
            'score': score_percentage,
            'passed': score_percentage >= 60,
            'next_url': f'/candidate/{token}/round2/' if score_percentage >= 60 else f'/candidate/{token}/results/'
        })
        
    except Exception as e:
        logger.error(f"Error submitting Round 1: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def candidate_round2(request, token):
    """
    Display Round 2 voice interview interface for candidates.
    """
    session = get_object_or_404(CandidateSession, token=token)
    
    # Redirect if Round 1 not completed
    if not session.completed_round1:
        return redirect('candidate_round1', token=token)
    
    # Redirect to results if Round 2 already completed
    if session.completed_round2:
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
    })

@csrf_exempt
@require_http_methods(["POST"])
def submit_audio_answer(request, token):
    """
    Handle audio answer submission, transcription, and AI evaluation.
    """
    logger.info(f"Audio submission request for token: {token}")
    
    try:
        # Validate session and question
        session = get_object_or_404(CandidateSession, token=token)
        question_id = request.POST.get('question_id')
        
        if not question_id:
            return JsonResponse({'error': 'Question ID required'}, status=400)
        
        question = get_object_or_404(Round2Question, id=question_id, hiring_request=session.hiring_request)
        
        # Validate audio file presence
        if 'audio' not in request.FILES:
            return JsonResponse({'error': 'No audio file provided'}, status=400)
        
        audio_file = request.FILES['audio']
        logger.info(f"Audio file received: {audio_file.name}, size: {audio_file.size} bytes")
        
        # Validate file size
        if audio_file.size > 10 * 1024 * 1024:
            return JsonResponse({'error': 'File too large. Maximum 10MB allowed.'}, status=400)
        
        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_audio:
            for chunk in audio_file.chunks():
                temp_audio.write(chunk)
            temp_audio_path = temp_audio.name
        
        try:
            # Step 1: Transcribe audio to text
            transcription_result = stt_client.transcribe_audio(temp_audio_path)
            logger.info(f"Transcription completed with success: {transcription_result.get('success', False)}")
            
            # Extract transcribed text safely
            transcribed_text = transcription_result.get('text', '')
            if not transcribed_text or len(transcribed_text.strip()) < 5:
                transcribed_text = "Audio could not be transcribed clearly. Please try speaking more clearly."
            
            # Log transcription snippet (safely)
            transcription_preview = transcribed_text[:100] + "..." if len(transcribed_text) > 100 else transcribed_text
            logger.info(f"Transcribed text: {transcription_preview}")
            
            # Step 2: Evaluate answer using Gemini AI
            evaluation = gemini_client.evaluate_voice_answer(
                question_text=question.question_text,
                model_answer=question.model_answer,
                candidate_answer=transcribed_text,
                difficulty_level=session.hiring_request.difficulty_level
            )
            
            logger.info(f"Gemini evaluation completed with score: {evaluation.get('score', 0)}")
            
            # Step 3: Save audio file permanently
            timestamp = int(time.time())
            file_name = f"answer_{session.token}_{question_id}_{timestamp}.webm"
            file_path = default_storage.save(f'audio/{file_name}', audio_file)
            
            # Step 4: Save answer to database
            round2_answer = Round2Answer(
                candidate_session=session,
                question=question,
                audio_response_path=file_path,
                transcribed_text=transcribed_text,
                score=evaluation.get('score', 0) * 100,  # Convert to percentage
                feedback=evaluation.get('explanation', ''),
                keywords_matched=evaluation.get('keywords_matched', []),
                improvement_suggestions=evaluation.get('improvement_suggestions', []),
                evaluation_confidence=evaluation.get('confidence', 0.0)
            )
            round2_answer.save()
            
            # Step 5: Update session progress
            current_index = session.current_question_index or 0
            session.current_question_index = current_index + 1
            
            # Check if all questions are answered
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
                
                # Calculate overall score (average of round1 and round2)
                round1_score = eval_result.round1_score or 0
                if round1_score > 0:
                    eval_result.overall_score = (round1_score + average_score) / 2
                else:
                    eval_result.overall_score = average_score
                    
                eval_result.is_shortlisted = eval_result.overall_score >= 60  # 60% threshold
                eval_result.save()
                
                overall_score = eval_result.overall_score
                is_shortlisted = eval_result.is_shortlisted
            
            session.save()
            
            # Prepare response data
            response_data = {
                'success': True,
                'transcription': transcribed_text,
                'score': round(round2_answer.score, 2),
                'feedback': round2_answer.feedback,
                'completed': completed,
                'progress': f"{answered_count}/{total_questions}",
                'current_question_index': session.current_question_index,
            }
            
            # Add completion data if interview is finished
            if completed:
                response_data['is_shortlisted'] = is_shortlisted
                response_data['overall_score'] = round(overall_score, 2)
                response_data['redirect_url'] = f'/candidate/{token}/results/'
            
            logger.info(f"Audio answer processed successfully. Completed: {completed}")
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Error processing audio answer: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Audio processing error: {str(e)}'
            }, status=500)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
        
    except Exception as e:
        logger.error(f"Error in audio submission endpoint: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

def candidate_results(request, token):
    """
    Display candidate results after completing both rounds.
    """
    session = get_object_or_404(CandidateSession, token=token)
    evaluation = get_object_or_404(EvaluationResult, candidate_session=session)
    
    return render(request, 'candidate/results.html', {
        'session': session,
        'evaluation': evaluation
    })

# =============================================================================
# API VIEWS
# =============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_generate_questions(request):
    """
    API endpoint to generate questions using Gemini AI.
    """
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
    """
    API endpoint to evaluate answers using Gemini AI.
    """
    try:
        data = json.loads(request.body)
        evaluation = gemini_client.evaluate_answer(
            question_rubric=data.get('rubric', ''),
            candidate_answer=data.get('answer', ''),
            question_type=data.get('type', 'short')
        )
        return JsonResponse(evaluation)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_synthesize_speech(request):
    """
    API endpoint for text-to-speech synthesis.
    """
    try:
        data = json.loads(request.body)
        text = data.get('text', 'Test question')
        
        logger.info(f"TTS request for text: {text[:50]}...")
        
        # Use ElevenLabs client for speech synthesis
        audio_path = elevenlabs_client.synthesize_text_to_audio(text)
        
        if audio_path and os.path.exists(audio_path):
            filename = os.path.basename(audio_path)
            media_url = f"/media/audio/{filename}"
            
            logger.info(f"Audio file ready: {media_url}")
            return JsonResponse({
                'audio_url': media_url,
                'file_path': audio_path,
                'mock': True,
                'status': 'success'
            })
        else:
            # Fallback to static file
            return JsonResponse({
                'audio_url': '/static/audio/sample.mp3',
                'mock': True,
                'status': 'fallback'
            })
            
    except Exception as e:
        logger.error(f"Error in TTS endpoint: {e}")
        return JsonResponse({
            'audio_url': '/static/audio/sample.mp3',
            'mock': True,
            'error': str(e),
            'status': 'error_fallback'
        }, status=500)

# =============================================================================
# RECRUITER RESULTS VIEWS
# =============================================================================

@login_required
def view_results(request, request_id):
    """
    Display candidate results for a specific hiring request.
    """
    hiring_request = get_object_or_404(HiringRequest, id=request_id, recruiter=request.user)
    candidate_sessions = CandidateSession.objects.filter(hiring_request=hiring_request)
    
    return render(request, 'recruiter/results.html', {
        'hiring_request': hiring_request,
        'candidate_sessions': candidate_sessions
    })

@login_required
def get_candidate_results(request, request_id):
    """
    API endpoint to get candidate results in JSON format.
    """
    hiring_request = get_object_or_404(HiringRequest, id=request_id, recruiter=request.user)
    candidate_sessions = CandidateSession.objects.filter(hiring_request=hiring_request)
    
    results = []
    for session in candidate_sessions:
        try:
            evaluation = EvaluationResult.objects.get(candidate_session=session)
            results.append({
                'token': str(session.token),
                'email': session.candidate_email,
                'completed_round1': session.completed_round1,
                'completed_round2': session.completed_round2,
                'round1_score': evaluation.round1_score,
                'round2_score': evaluation.round2_score,
                'overall_score': evaluation.overall_score,
                'is_shortlisted': evaluation.is_shortlisted,
                'created_at': session.created_at.isoformat()
            })
        except EvaluationResult.DoesNotExist:
            continue
    
    return JsonResponse({'results': results})

def welcome_page(request):
    """
    Display welcome page for the hiring agent application.
    """
    return render(request, 'welcome.html')