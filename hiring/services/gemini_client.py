import os
import json
import logging
import random
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.mock_mode = settings.MOCK_MODE
        
        if not self.mock_mode and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None
            logger.warning("Gemini client running in mock mode")

    def generate_questions(self, profile: str, years_experience: int, 
                          difficulty: str, n: int = 20) -> List[Dict[str, Any]]:
        """
        Generate assessment questions using Gemini API with diversity
        """
        if self.mock_mode or not self.model:
            return self._mock_generate_questions(profile, years_experience, difficulty, n)
        
        try:
            prompt = f"""
            You are an expert hiring-assistant. Generate {n} UNIQUE and DIVERSE assessment questions for role "{profile}" 
            with {years_experience} years experience at {difficulty} difficulty level.
            
            CRITICAL REQUIREMENTS:
            1. Each question must be completely unique - no repetition of concepts or phrasing
            2. Cover different categories: technical skills, problem-solving, behavioral, conceptual knowledge
            3. Mix question types appropriately (MCQ and short answer)
            4. Vary the difficulty based on the specified level
            5. Ensure questions are practical and job-relevant
            
            For MCQ questions:
            - Provide 4 plausible options with one clearly correct answer
            - Options should be realistic distractors
            - Mark the correct option with index (0-3)
            
            For short answer questions:
            - Ask open-ended questions that require thoughtful responses
            - Provide a comprehensive model answer
            
            Return JSON array of objects with exact fields:
            - id (integer, 1 to {n})
            - type (string: "mcq" or "short")
            - question (string: unique question text)
            - options (array of 4 strings, only for MCQ)
            - correct_option_index (integer 0-3, only for MCQ)
            - model_answer (string: expected answer/rubric)
            
            Example format for MCQ:
            {{
                "id": 1,
                "type": "mcq",
                "question": "What is the primary benefit of using version control in team development?",
                "options": [
                    "Enables collaborative coding and change tracking",
                    "Automatically fixes syntax errors",
                    "Improves internet connection speed",
                    "Generates code documentation automatically"
                ],
                "correct_option_index": 0,
                "model_answer": "Version control systems like Git enable multiple developers to work collaboratively, track changes, maintain history, and manage code versions efficiently."
            }}
            
            Example format for short answer:
            {{
                "id": 2,
                "type": "short", 
                "question": "Explain your approach to debugging a complex production issue under time pressure.",
                "options": null,
                "correct_option_index": null,
                "model_answer": "First, reproduce the issue in a controlled environment. Then use systematic debugging: check logs, isolate components, test hypotheses incrementally. Prioritize fixes based on impact and implement with proper testing before deployment."
            }}
            
            Ensure ALL {n} questions are completely different from each other.
            Return ONLY valid JSON parsable format.
            """
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean the response - remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]  # Remove ```json
            if response_text.startswith('```'):
                response_text = response_text[3:]  # Remove ```
            if response_text.endswith('```'):
                response_text = response_text[:-3]  # Remove ```
            
            questions_data = json.loads(response_text)
            
            # Validate we got the right number of questions
            if len(questions_data) != n:
                logger.warning(f"Requested {n} questions but got {len(questions_data)}. Using mock data as fallback.")
                return self._mock_generate_questions(profile, years_experience, difficulty, n)
            
            logger.info(f"Successfully generated {len(questions_data)} diverse questions for {profile}")
            return questions_data
            
        except Exception as e:
            logger.error(f"Error generating questions with Gemini: {e}")
            logger.info("Falling back to mock data with diversity")
            return self._mock_generate_questions(profile, years_experience, difficulty, n)

    def evaluate_answer(self, question_rubric: str, candidate_answer: str, 
                       question_type: str = "short") -> Dict[str, Any]:
        """
        Evaluate candidate answer against rubric using Gemini API with precision
        """
        if self.mock_mode or not self.model:
            return self._mock_evaluate_answer(question_rubric, candidate_answer, question_type)
        
        try:
            if question_type == "mcq":
                prompt = f"""
                Evaluate this multiple choice answer with high precision.
                
                QUESTION CONTEXT: The question tests knowledge relevant to the role.
                EXPECTED ANSWER: {question_rubric}
                CANDIDATE'S SELECTION: {candidate_answer}
                
                Analyze if the candidate's selection matches the expected correct answer.
                Consider both exact matching and conceptual understanding.
                
                Return JSON with exact structure:
                {{
                    "score": 1.0 or 0.0 (1.0 for correct, 0.0 for incorrect),
                    "confidence": 0.0 to 1.0 (certainty of evaluation),
                    "explanation": "Brief technical explanation of why the answer is correct/incorrect",
                    "keywords_matched": []
                }}
                """
            else:
                prompt = f"""
                Evaluate this short answer with high precision and fairness.
                
                EXPECTED ANSWER RUBRIC: {question_rubric}
                CANDIDATE'S ANSWER: {candidate_answer}
                
                Evaluation Criteria:
                1. Technical accuracy and completeness
                2. Relevance to the question asked
                3. Depth of understanding demonstrated
                4. Clarity and structure of response
                
                Scoring Guide:
                - 1.0: Excellent - Comprehensive, accurate, and well-explained
                - 0.8-0.9: Good - Mostly accurate with minor omissions
                - 0.6-0.7: Satisfactory - Basic understanding with some errors
                - 0.4-0.5: Poor - Significant errors or omissions
                - 0.0-0.3: Incorrect - Little to no relevant information
                
                Return JSON with exact structure:
                {{
                    "score": 0.0 to 1.0 (numeric score based on quality),
                    "confidence": 0.0 to 1.0 (your certainty in this evaluation),
                    "explanation": "Detailed technical feedback explaining the score",
                    "keywords_matched": ["list", "of", "relevant", "technical", "terms", "found"]
                }}
                
                Be strict but fair. Reward technical accuracy and punish significant errors.
                """
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            evaluation = json.loads(response_text)
            
            # Validate evaluation structure
            required_fields = ['score', 'confidence', 'explanation', 'keywords_matched']
            if all(field in evaluation for field in required_fields):
                return evaluation
            else:
                raise ValueError("Invalid evaluation format from Gemini")
                
        except Exception as e:
            logger.error(f"Error evaluating answer with Gemini: {e}")
            return self._mock_evaluate_answer(question_rubric, candidate_answer, question_type)

    def _mock_generate_questions(self, profile: str, years_experience: int, 
                               difficulty: str, n: int) -> List[Dict[str, Any]]:
        """Mock question generation with diversity for testing"""
        
        # Diverse question templates
        question_templates = [
            # Technical questions
            {
                'mcq': "What is the primary advantage of using {} in {} development?",
                'short': "Explain how you would implement {} in a {} project."
            },
            {
                'mcq': "Which tool is most appropriate for {} tasks in {} role?",
                'short': "Describe your troubleshooting approach for {} issues as a {}."
            },
            {
                'mcq': "What is the key consideration when working with {} as a {}?",
                'short': "How would you optimize {} performance for {} applications?"
            },
            # Conceptual questions
            {
                'mcq': "Which principle is most important for {} in {} scenarios?",
                'short': "Explain the significance of {} in modern {} development."
            },
            {
                'mcq': "What is the industry standard for {} implementation in {}?",
                'short': "Describe best practices for {} management in {} projects."
            },
            # Behavioral questions
            {
                'mcq': "How should a {} handle {} situations effectively?",
                'short': "Describe a scenario where {} skills were crucial for {} success."
            },
            {
                'mcq': "What is the most critical skill for {} with {} years experience?",
                'short': "Explain your methodology for {} planning in {} role."
            }
        ]
        
        # Technology and concept bank
        technologies = [
            "version control systems", "RESTful APIs", "database optimization", "code testing",
            "debugging techniques", "security practices", "performance monitoring", "CI/CD pipelines",
            "cloud services", "containerization", "code review processes", "agile methodology",
            "documentation standards", "error handling", "caching strategies", "load balancing",
            "microservices architecture", "API design", "data structures", "algorithm efficiency"
        ]
        
        questions = []
        used_combinations = set()
        
        for i in range(n):
            attempts = 0
            while attempts < 20:  # Increased attempts for better diversity
                template = random.choice(question_templates)
                question_type = "mcq" if (i + random.randint(0, 1)) % 2 == 0 else "short"
                tech = random.choice(technologies)
                
                question_text = template[question_type].format(tech, profile)
                question_hash = hash(question_text.lower().strip())
                
                if question_hash not in used_combinations:
                    used_combinations.add(question_hash)
                    break
                attempts += 1
            
            if question_type == "mcq":
                questions.append({
                    "id": i + 1,
                    "type": "mcq",
                    "question": question_text,
                    "options": self._generate_mcq_options(tech, profile),
                    "correct_option_index": 0,
                    "model_answer": f"The correct approach involves proper implementation of {tech} focusing on efficiency, maintainability, and adherence to {profile} best practices."
                })
            else:
                questions.append({
                    "id": i + 1,
                    "type": "short",
                    "question": question_text,
                    "options": None,
                    "correct_option_index": None,
                    "model_answer": f"A comprehensive answer should cover: understanding {tech} fundamentals, practical application in {profile} context, consideration of {difficulty} level requirements, and addressing real-world implementation challenges."
                })
        
        logger.info(f"Generated {len(questions)} diverse mock questions for {profile}")
        return questions

    def _generate_mcq_options(self, technology: str, profile: str) -> List[str]:
        """Generate realistic MCQ options"""
        base_options = [
            f"Proper implementation following {profile} standards",
            f"Inefficient approach that ignores best practices",
            f"Overly complex solution lacking practicality",
            f"Simplistic method missing critical {technology} considerations"
        ]
        
        # Shuffle but keep first option as correct
        options = base_options.copy()
        random.shuffle(options)
        options[0] = f"Correct application of {technology} principles"
        
        return options

    def _mock_evaluate_answer(self, question_rubric: str, candidate_answer: str, 
                            question_type: str) -> Dict[str, Any]:
        """Improved mock evaluation with better scoring"""
        if question_type == "mcq":
            # For MCQ, check if answer is reasonable
            if candidate_answer and len(candidate_answer.strip()) > 0:
                return {
                    "score": 1.0,
                    "confidence": 0.9,
                    "explanation": "MCQ answer submitted successfully",
                    "keywords_matched": ["selection_made"]
                }
            else:
                return {
                    "score": 0.0,
                    "confidence": 0.8,
                    "explanation": "No answer selected for MCQ",
                    "keywords_matched": []
                }
        
        # For short answers, more sophisticated mock evaluation
        candidate_lower = candidate_answer.lower()
        
        # Define relevant keywords based on question type
        technical_keywords = ["implement", "debug", "test", "optimize", "develop", "code", "algorithm", "function"]
        process_keywords = ["plan", "design", "analyze", "review", "document", "deploy", "monitor"]
        quality_keywords = ["efficient", "secure", "scalable", "maintainable", "reliable", "robust"]
        
        # Score based on answer length and keyword presence
        word_count = len(candidate_answer.split())
        length_score = min(word_count / 50, 1.0)  # Normalize by 50 words max
        
        # Keyword matching
        technical_match = any(keyword in candidate_lower for keyword in technical_keywords)
        process_match = any(keyword in candidate_lower for keyword in process_keywords)
        quality_match = any(keyword in candidate_lower for keyword in quality_keywords)
        
        keyword_score = (technical_match + process_match + quality_match) / 3.0
        overall_score = (length_score * 0.3) + (keyword_score * 0.7)
        
        matched_keywords = []
        if technical_match: matched_keywords.extend([kw for kw in technical_keywords if kw in candidate_lower])
        if process_match: matched_keywords.extend([kw for kw in process_keywords if kw in candidate_lower])
        if quality_match: matched_keywords.extend([kw for kw in quality_keywords if kw in candidate_lower])
        
        return {
            "score": round(overall_score, 2),
            "confidence": 0.8,
            "explanation": f"Answer demonstrates {'good' if overall_score > 0.6 else 'basic' if overall_score > 0.3 else 'limited'} understanding with {len(matched_keywords)} relevant concepts",
            "keywords_matched": list(set(matched_keywords))[:5]  # Remove duplicates, limit to 5
        }

    def evaluate_voice_answer(self, question_text: str, model_answer: str, 
                         candidate_answer: str, difficulty_level: str) -> Dict[str, Any]:
        """
        Evaluate voice answer with high precision using Gemini
        """
        if self.mock_mode or not self.model:
            return self._mock_evaluate_voice_answer(question_text, model_answer, candidate_answer, difficulty_level)
        
        try:
            prompt = f"""
            You are an expert technical interviewer evaluating a candidate's verbal response.
            
            QUESTION: "{question_text}"
            EXPECTED ANSWER RUBRIC: "{model_answer}"
            CANDIDATE'S VERBAL RESPONSE: "{candidate_answer}"
            DIFFICULTY LEVEL: {difficulty_level}
            
            Evaluation Criteria:
            1. TECHNICAL ACCURACY (40%): How correct is the technical content?
            2. COMPLETENESS (25%): Does it cover key points from the expected answer?
            3. RELEVANCE (20%): Is the response directly relevant to the question?
            4. CLARITY (15%): Is the response well-structured and understandable?
            
            Scoring Scale:
            - 0.9-1.0: Excellent - Comprehensive, accurate, and insightful
            - 0.7-0.8: Good - Mostly accurate with minor omissions
            - 0.5-0.6: Satisfactory - Basic understanding with some errors
            - 0.3-0.4: Poor - Significant errors or major omissions
            - 0.0-0.2: Incorrect - Little to no relevant information
            
            Consider that this was a verbal response - allow for some informal language
            but maintain technical rigor.
            
            Return JSON with exact structure:
            {{
                "score": 0.0 to 1.0 (precise numeric score),
                "confidence": 0.0 to 1.0 (your certainty in evaluation),
                "explanation": "Detailed technical feedback explaining strengths and weaknesses",
                "keywords_matched": ["list", "of", "relevant", "technical", "terms", "found"],
                "improvement_suggestions": ["specific", "suggestions", "for", "improvement"]
            }}
            
            Be fair but rigorous. Reward technical accuracy and punish significant errors.
            """
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            evaluation = json.loads(response_text)
            
            # Validate and enhance evaluation
            required_fields = ['score', 'confidence', 'explanation', 'keywords_matched']
            if all(field in evaluation for field in required_fields):
                # Ensure score is within bounds
                evaluation['score'] = max(0.0, min(1.0, float(evaluation['score'])))
                return evaluation
            else:
                raise ValueError("Invalid evaluation format from Gemini")
                
        except Exception as e:
            logger.error(f"Error evaluating voice answer with Gemini: {e}")
            return self._mock_evaluate_voice_answer(question_text, model_answer, candidate_answer, difficulty_level)

    def _mock_evaluate_voice_answer(self, question_text: str, model_answer: str,
                                candidate_answer: str, difficulty_level: str) -> Dict[str, Any]:
        """Mock evaluation for voice answers"""
        # More sophisticated mock evaluation for voice responses
        word_count = len(candidate_answer.split())
        
        # Basic quality metrics
        length_score = min(word_count / 100, 1.0)  # Normalize by 100 words
        
        # Keyword matching against model answer
        model_keywords = set(model_answer.lower().split())
        candidate_keywords = set(candidate_answer.lower().split())
        matched_keywords = model_keywords.intersection(candidate_keywords)
        
        keyword_score = len(matched_keywords) / max(len(model_keywords), 1)
        
        # Overall score combination
        overall_score = (length_score * 0.3) + (keyword_score * 0.7)
        
        return {
            "score": round(overall_score, 2),
            "confidence": 0.85,
            "explanation": f"Response shows {'strong' if overall_score > 0.7 else 'moderate' if overall_score > 0.5 else 'basic'} understanding. Matched {len(matched_keywords)} key concepts.",
            "keywords_matched": list(matched_keywords)[:10],
            "improvement_suggestions": ["Provide more specific examples", "Explain technical concepts in more detail"]
        }

    # Add this method to the GeminiClient class
    def generate_voice_interview_questions(self, profile: str, years_experience: int, 
                                        difficulty: str, n: int = 5) -> List[Dict[str, Any]]:
        """
        Generate voice interview questions specifically designed for verbal responses
        """
        if self.mock_mode or not self.model:
            return self._mock_generate_voice_questions(profile, years_experience, difficulty, n)
        
        try:
            prompt = f"""
            Generate {n} voice interview questions for role "{profile}" with {years_experience} years experience 
            at {difficulty} difficulty level. These questions are for a VOICE interview where candidates 
            will respond verbally (1-2 minute responses).
            
            Requirements:
            1. Questions should be open-ended and encourage detailed verbal responses
            2. Focus on practical experience, problem-solving, and behavioral aspects
            3. Questions should be suitable for audio recording (clear, concise, unambiguous)
            4. Include a comprehensive model answer/rubric for evaluation
            5. Questions should progress from basic to advanced based on difficulty
            
            Return JSON array with exact structure:
            [
                {{
                    "question": "Clear, concise question suitable for verbal response",
                    "model_answer": "Comprehensive expected answer covering key points, technical accuracy, and depth"
                }}
            ]
            
            Example:
            {{
                "question": "Describe a complex technical challenge you faced in {profile} and how you resolved it.",
                "model_answer": "Candidate should describe: specific challenge, technical approach, tools used, problem-solving process, outcome, and lessons learned. Key points: systematic debugging, collaboration if any, technical specifics relevant to {profile}."
            }}
            
            Generate {n} unique questions covering different aspects of {profile}.
            """
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean the response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            questions_data = json.loads(response_text)
            
            if len(questions_data) != n:
                logger.warning(f"Requested {n} voice questions but got {len(questions_data)}")
                return self._mock_generate_voice_questions(profile, years_experience, difficulty, n)
            
            logger.info(f"Successfully generated {len(questions_data)} voice interview questions")
            return questions_data
            
        except Exception as e:
            logger.error(f"Error generating voice interview questions: {e}")
            return self._mock_generate_voice_questions(profile, years_experience, difficulty, n)

    def _mock_generate_voice_questions(self, profile: str, years_experience: int, 
                                    difficulty: str, n: int) -> List[Dict[str, Any]]:
        """Mock voice interview questions"""
        question_templates = [
            {
                "question": f"Describe your experience with {profile} and how it prepared you for this role.",
                "model_answer": f"Should discuss relevant projects, technical skills, challenges overcome, and specific {profile} experience matching the role requirements."
            },
            {
                "question": f"What is your approach to problem-solving when facing technical challenges in {profile}?",
                "model_answer": f"Should explain systematic approach: problem analysis, research, solution design, implementation, testing. Should mention {profile}-specific tools/methods."
            },
            {
                "question": f"How do you ensure code quality and maintainability in {profile} projects?",
                "model_answer": f"Should discuss testing strategies, code reviews, documentation, best practices, and quality assurance processes specific to {profile}."
            },
            {
                "question": f"Can you describe a time when you had to learn a new technology quickly for a {profile} project?",
                "model_answer": f"Should demonstrate learning ability: research methods, practical application, challenges faced, and successful implementation in {profile} context."
            },
            {
                "question": f"What do you consider the most important emerging trend in {profile} and why?",
                "model_answer": f"Should show industry awareness: identify relevant trend, explain its significance, and discuss practical implications for {profile} work."
            }
        ]
        
        return question_templates[:n]

        