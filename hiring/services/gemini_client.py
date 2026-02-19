import imp
import os
import json
import logging
import random
from typing import List, Dict, Any
import google.generativeai as genai
from django.conf import settings
import requests
import re
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        try:
            # HARDCODED API KEY - DIRECT CONFIGURATION  
            api_key = "AIzaSyCBfbwr7_VVSnJcs1zsc1CfL_SgLNPNjS4"  # ✅ FIX: Correct working key
            
            if api_key:
        # This shows you if the key is being read correctly without revealing the whole thing
                print(f"DEBUG: Key found! Starts with: {api_key[:8]} and ends with: {api_key[-4:]}")
                print(f"DEBUG: Key length is: {len(api_key)}")
            else:
                print("DEBUG: API_KEY IS TOTALLY MISSING OR EMPTY - Check your .env file")
            # --------------------------

            if not api_key:
                raise ValueError("GEMINI_API_KEY not found")
            
            print(f"=== CONFIGURING GEMINI API ===")
            print(f"API Key: {api_key[:10]}...")
            
            # Configure with explicit API key - FORCE IT
            genai.configure(
                api_key=api_key,
                transport='rest'  # Force REST API instead of gRPC
            )
            
            # Create model with explicit configuration
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
            }
            
            self.model = genai.GenerativeModel(
                'gemini-pro',
                generation_config=generation_config
            )
            
            self.mock_mode = False
            logger.info("Gemini client initialized successfully with hardcoded API key")
            
            # Test the configuration
            print("✅ Gemini client configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            print(f"❌ Gemini client failed: {e}")
            self.model = None
            self.mock_mode = True    


    def generate_questions_with_gemini(self, work_profile, years_experience, difficulty_level, number_of_questions_round1):
        """
        Generate questions using DIRECT HTTP API - PROFILE-SPECIFIC VERSION
        """
        print(f"=== USING DIRECT HTTP API FOR GEMINI ===")
        print(f"Profile: {work_profile}, Experience: {years_experience}, Difficulty: {difficulty_level}, Questions: {number_of_questions_round1}")
        
        api_key = "AIzaSyCBfbwr7_VVSnJcs1zsc1CfL_SgLNPNjS4"
        
        
        if not api_key:
            print("❌ No API key found")
            return self.get_fallback_questions(number_of_questions_round1)
        
        # DYNAMIC PROMPT BASED ON WORK PROFILE
        if "aws" in work_profile.lower() or "cloud" in work_profile.lower():
            profile_focus = """
            FOCUS EXCLUSIVELY ON AWS SERVICES AND CONCEPTS:
            - AWS compute services (EC2, Lambda, ECS, EKS)
            - AWS storage services (S3, EBS, EFS)
            - AWS database services (RDS, DynamoDB, Redshift)
            - AWS networking (VPC, Subnets, Security Groups, Route Tables)
            - AWS security (IAM, KMS, WAF, Shield)
            - AWS monitoring (CloudWatch, CloudTrail)
            - AWS deployment (CloudFormation, CodeDeploy)
            - NO general programming questions
            """
        elif "python" in work_profile.lower():
            profile_focus = """
            FOCUS ON PYTHON PROGRAMMING AND RELATED TECHNOLOGIES:
            - Python syntax and data structures
            - Object-oriented programming in Python
            - Python frameworks (Django, Flask, FastAPI)
            - Database integration with Python
            - Python testing and debugging
            - Python best practices and patterns
            """
        elif "java" in work_profile.lower():
            profile_focus = """
            FOCUS ON JAVA PROGRAMMING AND RELATED TECHNOLOGIES:
            - Java syntax and OOP concepts
            - Spring framework (Boot, MVC, Security)
            - Java collections and data structures
            - Multithreading and concurrency
            - Java build tools (Maven, Gradle)
            - Java testing (JUnit, Mockito)
            """
        elif "frontend" in work_profile.lower() or "react" in work_profile.lower() or "angular" in work_profile.lower():
            profile_focus = """
            FOCUS ON FRONTEND DEVELOPMENT:
            - HTML5, CSS3, JavaScript (ES6+)
            - React.js/Angular/Vue.js frameworks
            - Responsive web design
            - State management
            - Web performance optimization
            - Browser APIs and DOM manipulation
            """
        elif "devops" in work_profile.lower():
            profile_focus = """
            FOCUS ON DEVOPS AND INFRASTRUCTURE:
            - CI/CD pipelines
            - Containerization (Docker, Kubernetes)
            - Infrastructure as Code (Terraform, CloudFormation)
            - Monitoring and logging
            - Cloud platforms (AWS, Azure, GCP)
            - Configuration management
            """
        else:
            profile_focus = f"""
            FOCUS ON {work_profile.upper()} SPECIFIC TECHNOLOGIES AND CONCEPTS:
            - Core technologies and frameworks relevant to this role
            - Industry best practices and standards
            - Real-world scenarios and problem-solving
            - Tools and methodologies used in this field
            """
        
        prompt = f"""
        Create exactly {number_of_questions_round1} technical questions for a {work_profile} role.
        Experience: {years_experience} years
        Difficulty: {difficulty_level}
        
        {profile_focus}
        
        DISTRIBUTION: 60% multiple choice, 40% short answer
    
        ALL QUESTIONS MUST BE SPECIFIC TO THIS ROLE AND RELEVANT TO THE EXPERIENCE LEVEL.
        IMPORTANT: For multiple choice questions, you MUST ensure the correct answer is TECHNICALLY ACCURATE.
        Double-check that the correct_option_index points to the ACTUALLY CORRECT technical answer.
            
        Return ONLY valid JSON with exactly {number_of_questions_round1} questions in this format:
        {{
            "questions": [
                {{
                    "id": 1,
                    "question_text": "Role-specific technical question?",
                    "question_type": "mcq",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": 0,
                    "model_answer": "Technical explanation specific to this role"
                }},
                {{
                    "id": 2,
                    "question_text": "Role-specific scenario question?",
                    "question_type": "short_answer",
                    "model_answer": "Comprehensive answer with role-specific details"
                }}
            ]
        }}
        """

        try:
            import requests
            import json as json_lib
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "topK": 20,
                    "topP": 0.8,
                    "maxOutputTokens": 8192,
                }
            }
            
            print("=== SENDING REQUEST TO GEMINI API ===")
            response = requests.post(url, json=data, timeout=60)
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                response_text = result['candidates'][0]['content']['parts'][0]['text']
                
                print(f"=== RAW RESPONSE RECEIVED ===")
                print(f"Response length: {len(response_text)} characters")
                
                # Enhanced cleaning
                cleaned_text = self._clean_and_validate_json(response_text)
                
                if not cleaned_text:
                    print("❌ Failed to extract valid JSON from response")
                    return self.get_fallback_questions(number_of_questions_round1)
                
                print(f"✓ Cleaned JSON length: {len(cleaned_text)} chars")
                
                try:
                    # Parse JSON response
                    questions_data = json_lib.loads(cleaned_text)
                    
                    # Validate the structure
                    if 'questions' not in questions_data:
                        print("❌ Invalid JSON structure: 'questions' key not found")
                        return self.get_fallback_questions(number_of_questions_round1)
                    
                    questions = questions_data['questions']
                    
                    print(f"✅ SUCCESS: Generated {len(questions)} {work_profile}-specific questions via HTTP API")
                    
                    # If we got fewer questions, make additional requests
                    if len(questions) < number_of_questions_round1:
                        print(f"⚠️ Got {len(questions)} questions, expected {number_of_questions_round1}")
                        additional_needed = number_of_questions_round1 - len(questions)
                        print(f"Making additional request for {additional_needed} questions...")
                        
                        # Recursive call to get remaining questions
                        additional_questions = self.generate_questions_with_gemini(
                            work_profile, years_experience, difficulty_level, additional_needed
                        )
                        
                        # Update IDs for additional questions
                        for i, q in enumerate(additional_questions):
                            q['id'] = len(questions) + i + 1
                        
                        questions.extend(additional_questions)
                        print(f"✅ Combined {len(questions)} total {work_profile}-specific questions")
                    
                    return questions
                    
                except json_lib.JSONDecodeError as e:
                    print(f"❌ JSON parsing error after cleaning: {e}")
                    return self.get_fallback_questions(number_of_questions_round1)
            else:
                print(f"❌ API Error: {response.status_code} - {response.text}")
                return self.get_fallback_questions(number_of_questions_round1)
                
        except Exception as e:
            print(f"❌ ERROR in direct HTTP API call: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return self.get_fallback_questions(number_of_questions_round1)
            
    def _get_additional_questions(self, work_profile, years_experience, difficulty_level, count):
        """Get additional questions if first request didn't return enough"""
        try:
            api_key = "AIzaSyCBfbwr7_VVSnJcs1zsc1CfL_SgLNPNjS4"  # ✅ FIX: Correct working key
            

            prompt = f"""
            Create exactly {count} additional technical questions for an {work_profile} role.
            Experience: {years_experience} years
            Difficulty: {difficulty_level}
            
            Focus on different AWS services and Python concepts than previous questions.
            
            Return ONLY valid JSON with {count} questions in the same format.
            """
            
            import requests
            import json as json_lib
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 4096,
                }
            }
            
            response = requests.post(url, json=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result['candidates'][0]['content']['parts'][0]['text']
                
                cleaned_text = self._clean_and_validate_json(response_text)
                if cleaned_text:
                    questions_data = json_lib.loads(cleaned_text)
                    if 'questions' in questions_data:
                        additional = questions_data['questions'][:count]  # Take only needed count
                        print(f"✅ Got {len(additional)} additional questions")
                        return additional
            
            # If additional request fails, use fallback
            print("⚠️ Additional request failed, using fallback questions")
            return self.get_fallback_questions(count)
            
        except Exception as e:
            print(f"❌ Error in additional questions request: {e}")
            return self.get_fallback_questions(count)


    def _debug_save_response(self, response_text: str, filename: str):
        """Save raw response for debugging"""
        try:
            import os
            debug_dir = "debug_responses"
            os.makedirs(debug_dir, exist_ok=True)
            filepath = os.path.join(debug_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(response_text)
            print(f"✓ Debug response saved: {filepath}")
        except Exception as e:
            print(f"❌ Could not save debug file: {e}")

    def _clean_and_validate_json(self, response_text: str) -> str:
        """
        Robust JSON cleaning and validation with multiple fallback strategies
        """
        try:
            print("=== CLEANING JSON RESPONSE ===")
            
            # Remove markdown code blocks first
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
                print("✓ Removed ```json markers")
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
                print("✓ Removed ``` markers")
            
            response_text = response_text.strip()
            print(f"Text after initial cleaning: {len(response_text)} chars")
            
            # Strategy 1: Try direct parsing first
            try:
                import json
                json.loads(response_text)
                print("✓ JSON is valid without modification")
                return response_text
            except json.JSONDecodeError as e:
                print(f"Initial JSON parse failed: {e}")
            
            # Strategy 2: Extract JSON using regex to find the JSON object
            import re  # ADD THIS IMPORT
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
                print("✓ Extracted JSON using regex")
                
                # Try parsing again
                try:
                    import json
                    json.loads(response_text)
                    print("✓ Extracted JSON is valid")
                    return response_text
                except json.JSONDecodeError as e2:
                    print(f"Extracted JSON still invalid: {e2}")
            
            # Strategy 3: Manual JSON repair for common issues
            repaired_json = self._repair_json(response_text)
            if repaired_json:
                try:
                    import json
                    json.loads(repaired_json)
                    print("✓ Repaired JSON is valid")
                    return repaired_json
                except json.JSONDecodeError:
                    print("✗ Repaired JSON still invalid")
            
            # Strategy 4: Last resort - extract just the questions array
            questions_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
            if questions_match:
                questions_array = questions_match.group(0)
                wrapped_json = f'{{"questions": {questions_array}}}'
                try:
                    import json
                    json.loads(wrapped_json)
                    print("✓ Successfully wrapped questions array")
                    return wrapped_json
                except json.JSONDecodeError:
                    print("✗ Wrapped questions array still invalid")
            
            print("❌ All JSON cleaning strategies failed")
            return ""
            
        except Exception as e:
            print(f"❌ Unexpected error in JSON cleaning: {e}")
            return ""

    def _repair_json(self, json_text: str) -> str:
        """
        Attempt to repair common JSON syntax errors
        """
        try:
            print("Attempting JSON repair...")
            import re  # ADD THIS IMPORT
            
            # Fix 1: Add missing commas between objects in array
            # Pattern: } { becomes }, {
            json_text = re.sub(r'\}\s*\{', '}, {', json_text)
            
            # Fix 2: Remove trailing commas before }
            json_text = re.sub(r',\s*}', '}', json_text)
            json_text = re.sub(r',\s*]', ']', json_text)
            
            # Fix 3: Ensure all strings are properly quoted
            # This is complex, so we'll focus on common patterns
            
            # Fix 4: Remove any text before first { and after last }
            start_idx = json_text.find('{')
            end_idx = json_text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_text = json_text[start_idx:end_idx+1]
            
            # Fix 5: Ensure the structure has "questions" key
            if '"questions"' not in json_text and 'questions' not in json_text:
                # Try to find array and wrap it
                array_match = re.search(r'\[\s*\{.*\}\s*\]', json_text, re.DOTALL)
                if array_match:
                    json_text = f'{{"questions": {array_match.group(0)}}}'
            
            print("✓ JSON repair completed")
            return json_text
            
        except Exception as e:
            print(f"❌ Error during JSON repair: {e}")
            return json_text

    def get_fallback_questions(self, num_questions):
        """
        Fallback questions when Gemini fails - COMPLETE FUNCTION
        """
        print(f"=== GEMINI CLIENT: Using fallback questions ===")
        
        # High-quality technical questions
        technical_questions = [
            # MCQs - Python specific
            {
                'question_text': 'What is the time complexity of accessing an element in a Python dictionary?',
                'question_type': 'mcq',
                'options': ['O(1) - Constant time', 'O(n) - Linear time', 'O(log n) - Logarithmic time', 'O(n²) - Quadratic time'],
                'correct_answer': 0,
                'model_answer': 'Dictionary access is O(1) on average due to hash table implementation'
            },
            {
                'question_text': 'Which method is called when an object is created in Python?',
                'question_type': 'mcq',
                'options': ['__init__ method', '__new__ method', '__create__ method', '__start__ method'],
                'correct_answer': 1,
                'model_answer': '__new__ creates the object instance, __init__ initializes it'
            },
            {
                'question_text': 'What does the "yield" keyword do in Python?',
                'question_type': 'mcq',
                'options': ['Returns a value and stops function execution', 'Creates a generator function', 'Raises a yield exception', 'Imports a yield module'],
                'correct_answer': 1,
                'model_answer': 'yield creates a generator function that can pause and resume execution'
            },
            {
                'question_text': 'What is the difference between "==" and "is" in Python?',
                'question_type': 'mcq',
                'options': ['"==" compares values, "is" compares identities', '"==" compares identities, "is" compares values', 'They are identical', '"is" is deprecated'],
                'correct_answer': 0,
                'model_answer': '"==" checks value equality, "is" checks if two variables point to the same object'
            },
            {
                'question_text': 'How do you create a virtual environment in Python?',
                'question_type': 'mcq',
                'options': ['python -m venv myenv', 'virtualenv create myenv', 'pip create venv myenv', 'python create virtual myenv'],
                'correct_answer': 0,
                'model_answer': 'python -m venv myenv creates a virtual environment named myenv'
            },
            
            # Short Answer Questions
            {
                'question_text': 'Explain the difference between lists and tuples in Python',
                'question_type': 'short_answer',
                'correct_answer': 'Lists are mutable (can be modified), tuples are immutable. Lists use [], tuples use (). Lists have more methods available.'
            },
            {
                'question_text': 'What are Python decorators and how do you use them?',
                'question_type': 'short_answer', 
                'correct_answer': 'Decorators are functions that modify other functions. They use @decorator_name syntax and are used for adding functionality to existing functions.'
            },
            {
                'question_text': 'Explain how exception handling works in Python',
                'question_type': 'short_answer',
                'correct_answer': 'Python uses try-except blocks. Code in try block is executed, if exception occurs, except block handles it. Finally block always executes.'
            },
            {
                'question_text': 'What is the purpose of __init__.py files in Python?',
                'question_type': 'short_answer',
                'correct_answer': '__init__.py files make directories into Python packages. They can contain initialization code and define what gets imported from the package.'
            },
            {
                'question_text': 'How does garbage collection work in Python?',
                'question_type': 'short_answer',
                'correct_answer': 'Python uses reference counting and generational garbage collection. Objects are deleted when reference count reaches zero or by cyclic garbage collector.'
            }
        ]
        
        # Ensure we have enough questions
        questions = []
        for i in range(num_questions):
            base_q = technical_questions[i % len(technical_questions)]
            questions.append({
                'id': i + 1,
                'question_text': base_q['question_text'],
                'question_type': base_q['question_type'],
                'options': base_q.get('options', []),
                'correct_answer': base_q.get('correct_answer', 0),
                'model_answer': base_q.get('model_answer', '')
            })
        
        print(f"✅ Created {len(questions)} improved fallback questions")
        return questions

    
    def _build_specific_question_prompt(self, profile: str, years_experience: int, 
                                      difficulty: str, n: int) -> str:
        """
        Build a highly specific prompt that forces Gemini to generate profile-specific,
        experience-appropriate technical questions.
        """
        # Calculate question distribution (60% MCQ, 40% Short Answer)
        mcq_count = int(n * 0.6)
        short_count = n - mcq_count
        
        return f"""
        You are a senior technical interviewer creating a technical assessment for a {profile} position.
        
        CANDIDATE PROFILE SPECIFICS:
        - Job Role: {profile}
        - Years of Experience: {years_experience} years
        - Difficulty Level: {difficulty}
        - Total Questions Needed: {n} ({mcq_count} MCQs, {short_count} Short Answer)
        
        CRITICAL REQUIREMENTS:
        1. Questions MUST be HIGHLY TECHNICAL and SPECIFIC to {profile} role
        2. Difficulty must match {difficulty} level for someone with {years_experience} years experience
        3. Each question must test ACTUAL JOB-RELATED SKILLS and TECHNICAL KNOWLEDGE
        4. NO generic questions like "What are key skills for {profile}?" or "Describe your experience"
        5. All questions must be UNIQUE and NON-REPETITIVE
        
        TECHNICAL DEPTH BY EXPERIENCE LEVEL:
        {self._get_technical_depth_guidance(profile, years_experience, difficulty)}
        
        QUESTION TYPE REQUIREMENTS:
        
        For Multiple Choice Questions ({mcq_count} questions):
        - Must have exactly 4 TECHNICAL options
        - Options should be PLAUSIBLE but only ONE is technically correct
        - Include correct_option_index (0-3)
        - Focus on technical concepts, tools, and problem-solving
        
        For Short Answer Questions ({short_count} questions):
        - Should require 3-8 sentences to answer properly
        - Focus on practical application, architecture, and problem-solving
        - Test depth of technical understanding
        
        OUTPUT FORMAT:
        Return ONLY a valid JSON array with this exact structure:
        [
            {{
                "id": 1,
                "type": "mcq",
                "question": "Highly technical, profile-specific question...",
                "options": ["Technical Option A", "Technical Option B", "Technical Option C", "Technical Option D"],
                "correct_option_index": 0,
                "model_answer": "Detailed technical explanation of why this is correct and others are wrong"
            }},
            {{
                "id": 2,
                "type": "short", 
                "question": "Technical scenario requiring detailed explanation...",
                "options": null,
                "correct_option_index": null,
                "model_answer": "Comprehensive technical answer with best practices"
            }}
        ]
        
        Generate exactly {n} questions that would genuinely assess a {profile} with {years_experience} years experience at {difficulty} level.
        Focus on REAL TECHNICAL CONTENT that this professional would encounter daily.
        """

    def _get_technical_depth_guidance(self, profile: str, years_experience: int, difficulty: str) -> str:
        """
        Provide highly specific technical guidance based on profile, experience, and difficulty
        """
        base_guidance = f"For a {profile} with {years_experience} years experience at {difficulty} level:\n"
        
        # Profile-specific technical focus areas
        profile_focus = {
            'python developer': {
                'beginner': 'Focus on basic Python syntax, data structures (list, tuple, dict, set), functions, OOP basics, file handling, simple algorithms',
                'intermediate': 'Cover advanced OOP, decorators, generators, context managers, popular libraries (requests, pandas, numpy), web frameworks basics, database integration',
                'expert': 'Deep dive into metaprogramming, async programming, performance optimization, advanced frameworks (Django/Flask internals), system design, architecture patterns, testing strategies'
            },
            'aws engineer': {
                'beginner': 'Focus on basic AWS services (EC2, S3, IAM), simple deployments, basic security concepts, cost management fundamentals',
                'intermediate': 'Cover advanced services (Lambda, RDS, CloudFront), infrastructure as code (CloudFormation/Terraform), monitoring (CloudWatch), networking (VPC), security best practices',
                'expert': 'Deep architecture design, multi-region deployments, advanced security (KMS, Security Hub), cost optimization strategies, DevOps practices, containerization (ECS/EKS), serverless architectures'
            },
            'devops engineer': {
                'beginner': 'Focus on basic CI/CD concepts, version control (Git), simple scripting, basic containerization, monitoring fundamentals',
                'intermediate': 'Cover advanced CI/CD pipelines, infrastructure as code, configuration management, container orchestration basics, cloud services integration, monitoring tools',
                'expert': 'Deep dive into advanced orchestration, infrastructure automation, security in DevOps, performance optimization, disaster recovery, multi-cloud strategies, SRE practices'
            },
            'java developer': {
                'beginner': 'Focus on Java basics, OOP principles, collections framework, exception handling, basic multithreading, JDBC fundamentals',
                'intermediate': 'Cover advanced Java features (streams, lambdas), Spring framework, JPA/Hibernate, web services (REST/SOAP), build tools (Maven/Gradle), testing frameworks',
                'expert': 'Deep JVM internals, performance tuning, microservices architecture, advanced Spring (Boot, Cloud, Security), distributed systems, design patterns implementation'
            },
            'frontend developer': {
                'beginner': 'Focus on HTML5, CSS3, JavaScript basics, DOM manipulation, responsive design principles, basic React/Vue components',
                'intermediate': 'Cover advanced JavaScript (ES6+), state management, modern frameworks (React/Vue/Angular), build tools, API integration, performance optimization',
                'expert': 'Deep dive into advanced framework concepts, web performance, PWA, testing strategies, architecture patterns, build optimization, cross-browser compatibility'
            },
            'data scientist': {
                'beginner': 'Focus on basic statistics, data cleaning, simple ML algorithms, data visualization fundamentals',
                'intermediate': 'Cover advanced ML models, feature engineering, model evaluation, big data tools, statistical analysis',
                'expert': 'Deep dive into advanced algorithms, deep learning, model deployment, MLOps, data pipeline architecture, business impact analysis'
            },
            'machine learning engineer': {
                'beginner': 'Focus on basic ML concepts, simple model training, data preprocessing, evaluation metrics',
                'intermediate': 'Cover model optimization, hyperparameter tuning, deployment basics, ML pipelines, feature stores',
                'expert': 'Deep architecture design, distributed training, model serving, ML system design, performance optimization, production monitoring'
            }
        }
        
        # Get specific guidance for the profile or provide general guidance
        if profile.lower() in profile_focus:
            profile_guidance = profile_focus[profile.lower()].get(difficulty, 'Cover advanced technical concepts, architecture, and real-world problem-solving')
        else:
            # General guidance for unknown profiles
            if years_experience == 0:
                profile_guidance = 'Focus on fundamental concepts, basic tools, core principles, and learning ability specific to this role.'
            elif years_experience <= 2:
                profile_guidance = 'Include practical implementation, common tools/frameworks, basic architecture, and hands-on technical skills.'
            elif years_experience <= 4:
                profile_guidance = 'Cover advanced concepts, optimization techniques, architecture patterns, and system design principles.'
            else:
                profile_guidance = 'Focus on complex problem-solving, system architecture, scalability, technical leadership, and strategic decision-making.'
        
        return base_guidance + profile_guidance

    def _create_improved_fallback_questions(self, profile: str, years_experience: int,
                                          difficulty: str, n: int, start_id: int = 1) -> List[Dict[str, Any]]:
        """
        Create improved fallback questions that are more profile-specific
        """
        questions = []
        
        # Create a mix of MCQs and short answer questions
        mcq_count = int(n * 0.6)
        short_count = n - mcq_count
        
        # Generate profile-specific MCQs
        for i in range(mcq_count):
            tech_concept = self._get_profile_specific_concept(profile, years_experience, difficulty)
            questions.append({
                "id": start_id + i,
                "type": "mcq",
                "question": f"As a {profile}, how would you technically approach {tech_concept} considering {years_experience} years experience?",
                "options": [
                    f"{self._get_technical_option(profile, 'correct', tech_concept)}",
                    f"{self._get_technical_option(profile, 'incorrect', tech_concept)}", 
                    f"{self._get_technical_option(profile, 'partial', tech_concept)}",
                    f"{self._get_technical_option(profile, 'wrong', tech_concept)}"
                ],
                "correct_option_index": 0,
                "model_answer": f"The correct approach for a {profile} with {years_experience} years experience involves {self._get_correct_approach(profile, tech_concept)}. This demonstrates proper understanding of {tech_concept} at {difficulty} level."
            })
        
        # Generate profile-specific short answer questions
        for i in range(short_count):
            scenario = self._get_profile_specific_scenario(profile, years_experience, difficulty)
            questions.append({
                "id": start_id + mcq_count + i,
                "type": "short",
                "question": f"Describe the technical architecture and implementation strategy for {scenario} as a {profile} with {years_experience} years experience.",
                "options": None,
                "correct_option_index": None,
                "model_answer": f"A comprehensive technical answer should cover: {self._get_expected_answer_elements(profile, scenario, years_experience, difficulty)}. The response should demonstrate {difficulty}-level expertise in {profile} responsibilities."
            })
        
        # Shuffle questions to mix types
        random.shuffle(questions)
        
        # Reassign IDs after shuffling
        for i, question in enumerate(questions):
            question['id'] = start_id + i
        
        logger.info(f"Created {len(questions)} improved fallback questions for {profile}")
        return questions

    def _get_profile_specific_concept(self, profile: str, years_experience: int, difficulty: str) -> str:
        """Get profile-specific technical concepts based on experience and difficulty"""
        concepts = {
            'python developer': {
                'beginner': ['implementing a function to reverse a string', 'creating a class for a simple bank account', 'handling file I/O operations', 'using list comprehensions effectively', 'working with dictionaries and sets'],
                'intermediate': ['designing a REST API with Flask', 'optimizing database queries in Django', 'implementing caching strategies', 'writing unit tests for complex functions', 'using decorators for cross-cutting concerns'],
                'expert': ['designing a microservices architecture', 'implementing async programming patterns', 'optimizing application performance', 'designing a scalable data processing pipeline', 'building custom context managers']
            },
            'aws engineer': {
                'beginner': ['setting up a basic EC2 instance', 'configuring S3 bucket policies', 'creating IAM roles and policies', 'setting up basic monitoring', 'deploying a simple web application'],
                'intermediate': ['designing a multi-tier architecture', 'implementing auto-scaling groups', 'configuring VPC networking', 'setting up CI/CD pipeline', 'migrating databases to RDS'],
                'expert': ['designing a multi-region disaster recovery strategy', 'implementing advanced security controls', 'optimizing cloud costs across services', 'designing serverless architectures', 'building event-driven architectures']
            },
            'devops engineer': {
                'beginner': ['setting up a basic CI/CD pipeline', 'writing a simple Dockerfile', 'configuring basic monitoring', 'managing version control workflows', 'deploying a containerized application'],
                'intermediate': ['implementing infrastructure as code', 'configuring container orchestration', 'setting up log aggregation', 'managing configuration across environments', 'implementing blue-green deployments'],
                'expert': ['designing a GitOps workflow', 'implementing advanced security scanning', 'optimizing pipeline performance', 'designing multi-cloud deployment strategies', 'building self-healing systems']
            },
            'java developer': {
                'beginner': ['implementing basic OOP concepts', 'working with collections framework', 'handling exceptions properly', 'writing simple JDBC code', 'understanding basic multithreading'],
                'intermediate': ['designing Spring Boot applications', 'implementing RESTful web services', 'working with JPA and Hibernate', 'writing comprehensive unit tests', 'using design patterns effectively'],
                'expert': ['designing microservices architecture', 'optimizing JVM performance', 'implementing reactive programming', 'building distributed systems', 'designing complex data processing pipelines']
            }
        }
        
        # Default concepts if profile not found
        default_concepts = {
            'beginner': ['basic implementation', 'fundamental concepts', 'simple configuration', 'essential practices'],
            'intermediate': ['advanced implementation', 'complex scenarios', 'optimization techniques', 'architecture considerations'],
            'expert': ['strategic design', 'performance optimization', 'scalability solutions', 'advanced architecture']
        }
        
        profile_lower = profile.lower()
        if profile_lower in concepts and difficulty in concepts[profile_lower]:
            return random.choice(concepts[profile_lower][difficulty])
        else:
            return random.choice(default_concepts.get(difficulty, default_concepts['intermediate']))

    def _get_technical_option(self, profile: str, option_type: str, concept: str) -> str:
        """Generate technical options based on profile and concept"""
        bases = {
            'correct': [
                f"Apply industry best practices for {concept}",
                f"Use the most efficient approach for {concept}",
                f"Implement scalable solution for {concept}",
                f"Follow security-first approach for {concept}"
            ],
            'incorrect': [
                f"Use deprecated methods for {concept}",
                f"Ignore security considerations in {concept}",
                f"Choose inefficient implementation for {concept}",
                f"Violate best practices for {concept}"
            ],
            'partial': [
                f"Partially correct but incomplete approach to {concept}",
                f"Works but doesn't scale well for {concept}",
                f"Correct but inefficient method for {concept}",
                f"Valid but not optimal solution for {concept}"
            ],
            'wrong': [
                f"Completely incorrect approach to {concept}",
                f"Technically flawed solution for {concept}",
                f"Implementation that would fail for {concept}",
                f"Approach that violates core principles of {concept}"
            ]
        }
        return random.choice(bases.get(option_type, bases['incorrect']))

    def _get_profile_specific_scenario(self, profile: str, years_experience: int, difficulty: str) -> str:
        """Get profile-specific technical scenarios"""
        scenarios = {
            'python developer': {
                'beginner': 'building a simple web scraper',
                'intermediate': 'developing a RESTful API with authentication',
                'expert': 'designing a real-time data processing system'
            },
            'aws engineer': {
                'beginner': 'deploying a simple web application',
                'intermediate': 'migrating an on-premise application to AWS',
                'expert': 'designing a highly available multi-region architecture'
            },
            'devops engineer': {
                'beginner': 'setting up a basic deployment pipeline',
                'intermediate': 'implementing blue-green deployment strategy',
                'expert': 'designing a complete GitOps workflow for microservices'
            },
            'java developer': {
                'beginner': 'building a simple CRUD application',
                'intermediate': 'developing a microservice with Spring Boot',
                'expert': 'designing a high-performance distributed system'
            }
        }
        
        profile_lower = profile.lower()
        if profile_lower in scenarios and difficulty in scenarios[profile_lower]:
            return scenarios[profile_lower][difficulty]
        else:
            return f"a {difficulty} level technical project appropriate for {years_experience} years experience"

    def _get_correct_approach(self, profile: str, concept: str) -> str:
        """Describe the correct technical approach"""
        approaches = {
            'python developer': f"using Python best practices, proper error handling, and efficient algorithms for {concept}",
            'aws engineer': f"following AWS well-architected framework principles for {concept}",
            'devops engineer': f"implementing automation, monitoring, and security best practices for {concept}",
            'java developer': f"applying Java design patterns and Spring framework best practices for {concept}",
            'default': f"applying industry standards and best practices specific to {profile} for {concept}"
        }
        return approaches.get(profile.lower(), approaches['default'])

    def _get_expected_answer_elements(self, profile: str, scenario: str, years_experience: int, difficulty: str) -> str:
        """Describe what a comprehensive answer should include"""
        elements = [
            f"technical architecture appropriate for {difficulty} level",
            f"consideration of {years_experience} years experience context",
            "implementation details and best practices",
            "scalability and performance considerations",
            "security and maintenance aspects"
        ]
        return ", ".join(elements)

    def _clean_json_response(self, response_text: str) -> str:
        """Clean the JSON response from Gemini"""
        # Remove markdown code blocks
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        elif response_text.startswith('```'):
            response_text = response_text[3:]
        
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        return response_text.strip()

    def _validate_question_structure(self, question: Dict) -> bool:
        """Validate that a question has the correct structure"""
        required_fields = ['type', 'question', 'model_answer']
        
        if not all(field in question for field in required_fields):
            return False
        
        if question['type'] == 'mcq':
            if 'options' not in question or 'correct_option_index' not in question:
                return False
            if not isinstance(question['options'], list) or len(question['options']) != 4:
                return False
            if not isinstance(question['correct_option_index'], int) or question['correct_option_index'] not in [0, 1, 2, 3]:
                return False
        
        return True

    def evaluate_answer(self, question_data: Dict[str, Any] = None, candidate_answer: str = None) -> Dict[str, Any]:
        """
        Evaluate answers using ONLY Gemini AI - no fallback methods
        """
        logger.info(f"=== GEMINI AI EVALUATION STARTED ===")
        logger.info(f"Question type: {question_data.get('question_type')}")
        logger.info(f"Question: {question_data.get('question_text', '')[:100]}...")
        logger.info(f"Candidate answer: '{candidate_answer}'")
        
        if question_data is None or candidate_answer is None:
            return {
                "score": 0.0,
                "confidence": 0.5,
                "explanation": "Evaluation error: Missing question data or answer.",
                "is_correct": False,
                "correct_answer": ""
            }
        
        question_type = question_data.get('question_type', 'short')
        
        # For MCQ questions, use precise evaluation first, then fallback to AI
        if question_type == "mcq":
            # First try precise evaluation
            precise_result = self._evaluate_mcq_answer(question_data, candidate_answer)
            if precise_result.get('confidence', 0) > 0.8:
                return precise_result
            else:
                # If precise evaluation is uncertain, use AI
                return self._evaluate_mcq_with_gemini(question_data, candidate_answer)
        else:
            # For short answers, use ONLY Gemini AI evaluation
            return self._evaluate_short_answer_with_gemini(question_data, candidate_answer)



    def _evaluate_mcq_answer(self, question_data: Dict, candidate_answer: str) -> Dict[str, Any]:
        """Evaluate MCQ answer with precise matching"""
        logger.info("=== MCQ EVALUATION ===")
        
        correct_index = question_data.get('correct_option_index', 0)
        options = question_data.get('options', [])
        
        logger.info(f"Correct index: {correct_index}")
        logger.info(f"Options: {options}")
        logger.info(f"Candidate answer: '{candidate_answer}'")
        
        if not options:
            logger.error("No options available for MCQ evaluation")
            return {
                "score": 0.0,
                "confidence": 0.5,
                "explanation": "Invalid question configuration - no options available.",
                "is_correct": False
            }
        
        if correct_index >= len(options):
            logger.error(f"Correct index {correct_index} out of bounds for options length {len(options)}")
            return {
                "score": 0.0,
                "confidence": 0.5,
                "explanation": "Invalid question configuration - correct index out of bounds.",
                "is_correct": False
            }
        
        correct_answer_text = options[correct_index]
        logger.info(f"Correct answer text: '{correct_answer_text}'")
        
        # METHOD 1: Check if candidate selected by OPTION INDEX (0,1,2,3)
        try:
            candidate_index = int(candidate_answer)
            if candidate_index == correct_index:
                logger.info("CORRECT - Candidate selected by index")
                return {
                    "score": 1.0,
                    "confidence": 1.0,
                    "explanation": f"Correct! You selected the right answer: {correct_answer_text}",
                    "is_correct": True,
                    "correct_answer": correct_answer_text,
                    "candidate_answer": candidate_answer
                }
            else:
                logger.info(f"INCORRECT - Candidate index {candidate_index} != correct index {correct_index}")
                return {
                    "score": 0.0,
                    "confidence": 1.0,
                    "explanation": f"Incorrect. The right answer is: {correct_answer_text}",
                    "is_correct": False,
                    "correct_answer": correct_answer_text,
                    "candidate_answer": candidate_answer
                }
        except (ValueError, TypeError):
            # Not an index, continue to other methods
            pass
        
        # METHOD 2: Check if candidate selected by OPTION LETTER (A,B,C,D)
        option_letters = ['A', 'B', 'C', 'D']
        candidate_upper = candidate_answer.upper().strip()
        if candidate_upper in option_letters:
            candidate_letter_index = option_letters.index(candidate_upper)
            if candidate_letter_index == correct_index:
                logger.info("CORRECT - Candidate selected by letter")
                return {
                    "score": 1.0,
                    "confidence": 1.0,
                    "explanation": f"Correct! You selected the right answer: {correct_answer_text}",
                    "is_correct": True,
                    "correct_answer": correct_answer_text,
                    "candidate_answer": candidate_answer
                }
            else:
                logger.info(f"INCORRECT - Candidate letter {candidate_upper} != correct index {correct_index}")
                return {
                    "score": 0.0,
                    "confidence": 1.0,
                    "explanation": f"Incorrect. The right answer is: {correct_answer_text}",
                    "is_correct": False,
                    "correct_answer": correct_answer_text,
                    "candidate_answer": candidate_answer
                }
        
        # METHOD 3: Check if candidate provided the exact OPTION TEXT
        normalized_correct = self._normalize_text(correct_answer_text)
        normalized_candidate = self._normalize_text(candidate_answer)
        
        if normalized_candidate == normalized_correct:
            logger.info("CORRECT - Exact text match")
            return {
                "score": 1.0,
                "confidence": 1.0,
                "explanation": f"Correct! You selected the right answer.",
                "is_correct": True,
                "correct_answer": correct_answer_text,
                "candidate_answer": candidate_answer
            }
        
        # METHOD 4: Check if candidate text matches any option text
        for i, option in enumerate(options):
            if self._normalize_text(candidate_answer) == self._normalize_text(option):
                if i == correct_index:
                    logger.info("CORRECT - Matched correct option text")
                    return {
                        "score": 1.0,
                        "confidence": 1.0,
                        "explanation": f"Correct! You selected the right answer: {correct_answer_text}",
                        "is_correct": True,
                        "correct_answer": correct_answer_text,
                        "candidate_answer": candidate_answer
                    }
                else:
                    logger.info(f"INCORRECT - Matched wrong option text at index {i}")
                    return {
                        "score": 0.0,
                        "confidence": 1.0,
                        "explanation": f"Incorrect. The right answer is: {correct_answer_text}",
                        "is_correct": False,
                        "correct_answer": correct_answer_text,
                        "candidate_answer": candidate_answer
                    }
        
        # If we get here, no match was found
        logger.info("INCORRECT - No match found")
        return {
            "score": 0.0,
            "confidence": 0.9,
            "explanation": f"Incorrect. The right answer is: {correct_answer_text}",
            "is_correct": False,
            "correct_answer": correct_answer_text,
            "candidate_answer": candidate_answer
        }



    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        if text is None:
            return ""
        return ' '.join(str(text).lower().strip().split())

    def _evaluate_mcq_with_gemini(self, question_data: Dict, candidate_answer: str) -> Dict[str, Any]:
        """
        Use Gemini AI to evaluate MCQ answers when precise matching fails
        """
        try:
            options = question_data.get('options', [])
            correct_index = question_data.get('correct_option_index', 0)
            correct_answer_text = options[correct_index] if correct_index < len(options) else ""
            
            prompt = f"""
            Evaluate this multiple choice question answer:
            
            QUESTION: "{question_data.get('question_text', '')}"
            
            OPTIONS:
            A) {options[0] if len(options) > 0 else ''}
            B) {options[1] if len(options) > 1 else ''}
            C) {options[2] if len(options) > 2 else ''}
            D) {options[3] if len(options) > 3 else ''}
            
            CORRECT ANSWER: {correct_answer_text}
            
            CANDIDATE'S ANSWER: "{candidate_answer}"
            
            Determine if the candidate's answer matches the correct answer. Consider:
            - Exact text matches
            - Option selection (A, B, C, D or 0, 1, 2, 3)
            - Semantic similarity
            
            Return your evaluation in this EXACT JSON format:
            {{
                "score": 1.0,
                "is_correct": true,
                "explanation": "The candidate selected the correct option...",
                "confidence": 0.95,
                "correct_answer": "{correct_answer_text}"
            }}
            
            Score should be 1.0 for correct, 0.0 for incorrect.
            """
            
            # Use direct HTTP API for evaluation
            api_key = "AIzaSyC4lfyxD20gaR5Pnji2aWUsw9ttM2S8eog"

            import requests
            import json as json_lib
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1024,
                }
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # Clean and parse JSON response
                cleaned_text = self._clean_and_validate_json(response_text)
                if cleaned_text:
                    evaluation = json_lib.loads(cleaned_text)
                    
                    # Validate and ensure score is within bounds
                    score = float(evaluation.get('score', 0.0))
                    evaluation['score'] = 1.0 if score >= 0.5 else 0.0
                    evaluation['is_correct'] = evaluation.get('is_correct', score >= 0.5)
                    evaluation['correct_answer'] = correct_answer_text
                    
                    logger.info(f"Gemini MCQ evaluation - Score: {evaluation['score']}, Correct: {evaluation['is_correct']}")
                    return evaluation
            
            # Fallback to precise evaluation
            return self._evaluate_mcq_answer(question_data, candidate_answer)
            
        except Exception as e:
            logger.error(f"Error in Gemini MCQ evaluation: {e}")
            return self._evaluate_mcq_answer(question_data, candidate_answer)

    def _evaluate_short_answer_with_gemini(self, question_data: Dict, candidate_answer: str) -> Dict[str, Any]:
        """
        Evaluate short answers using ONLY Gemini AI - no fallback
        """
        try:
            prompt = f"""
            You are an expert technical evaluator. Evaluate this answer strictly and accurately.

            QUESTION: "{question_data.get('question_text', '')}"
            
            CANDIDATE'S ANSWER: "{candidate_answer}"
            
            EXPECTED ANSWER GUIDELINES: "{question_data.get('model_answer', '')}"
            
            Evaluate the answer on a scale of 0.0 to 1.0 based on:
            1. Technical accuracy and correctness
            2. Completeness in addressing the question
            3. Relevance to the expected answer guidelines
            4. Depth of understanding demonstrated
            
            Return ONLY valid JSON in this exact format:
            {{
                "score": 0.85,
                "is_correct": true,
                "explanation": "Detailed technical feedback...",
                "confidence": 0.9,
                "correct_answer": "Brief summary of expected answer"
            }}
            
            Be strict and accurate in scoring.
            """
            
            # Use direct HTTP API for Gemini
            api_key = "AIzaSyCBfbwr7_VVSnJcs1zsc1CfL_SgLNPNjS4"  # ✅ FIX: Correct working key

            import requests
            import json as json_lib
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1024,
                }
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # Clean and parse JSON response
                cleaned_text = self._clean_and_validate_json(response_text)
                if cleaned_text:
                    evaluation = json_lib.loads(cleaned_text)
                    
                    # Validate and ensure score is within bounds
                    score = float(evaluation.get('score', 0.0))
                    evaluation['score'] = max(0.0, min(1.0, score))
                    evaluation['is_correct'] = evaluation.get('is_correct', score >= 0.6)
                    evaluation['correct_answer'] = question_data.get('model_answer', '')
                    
                    logger.info(f"Gemini short answer evaluation - Score: {evaluation['score']}, Correct: {evaluation['is_correct']}")
                    return evaluation
            
            # If we reach here, Gemini API failed - return minimal evaluation
            logger.error("Gemini API failed for short answer evaluation")
            return {
                "score": 0.5,
                "is_correct": False,
                "explanation": "Evaluation service temporarily unavailable.",
                "confidence": 0.5,
                "correct_answer": question_data.get('model_answer', '')
            }
            
        except Exception as e:
            logger.error(f"Error in Gemini short answer evaluation: {e}")
            # Return minimal evaluation instead of using fallback
            return {
                "score": 0.5,
                "is_correct": False,
                "explanation": "Evaluation service error.",
                "confidence": 0.3,
                "correct_answer": question_data.get('model_answer', '')
            }

    
    def evaluate_voice_answer(self, question_text: str, model_answer: str, candidate_answer: str,
                        difficulty_level: str, work_profile: str = None, years_experience: int = None) -> Dict[str, Any]:
        """
        Evaluate voice answers using ONLY Gemini AI - no fallback methods
        """
        logger.info(f"=== GEMINI VOICE ANSWER EVALUATION STARTED ===")
        logger.info(f"Question: {question_text}")
        logger.info(f"Model answer: {model_answer}")
        logger.info(f"Candidate answer: '{candidate_answer}'")
        
        # Validate input
        if not candidate_answer or len(candidate_answer.strip()) < 5:
            logger.warning("Voice answer too short or empty")
            return {
                "score": 0.0,
                "explanation": "Answer is too short or unclear. Please provide a more detailed response.",
                "confidence": 0.9,
                "keywords_matched": [],
                "improvement_suggestions": ["Provide a more detailed answer", "Speak clearly and completely"],
                "is_correct": False
            }
        
        try:
            # Use Gemini AI for evaluation
            prompt = f"""
            You are a technical interviewer evaluating a candidate's voice response.

            QUESTION: "{question_text}"
            
            CANDIDATE'S ANSWER: "{candidate_answer}"
            
            EXPECTED ANSWER: "{model_answer}"
            
            Compare the candidate's answer with the expected answer and provide an accurate score (0.0 to 1.0).
            
            Scoring criteria:
            - 0.9-1.0: Excellent - comprehensive, accurate, covers all key points
            - 0.7-0.89: Good - covers most key points, minor omissions
            - 0.5-0.69: Satisfactory - basic understanding, some errors
            - 0.3-0.49: Poor - significant errors or omissions
            - 0.1-0.29: Very poor - minimal relevant content
            - 0.0: No meaningful response
            
            Return ONLY valid JSON in this exact format:
            {{
                "score": 0.85,
                "explanation": "Detailed comparison with expected answer...",
                "confidence": 0.9,
                "keywords_matched": ["key", "terms", "matched"],
                "improvement_suggestions": ["suggestion1", "suggestion2"],
                "is_correct": true
            }}
            """
            
            # Use direct HTTP API for Gemini
            api_key = "AIzaSyC4lfyxD20gaR5Pnji2aWUsw9ttM2S8eog"
            import requests
            import json as json_lib
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1024,
                }
            }
            
            logger.info("Sending voice evaluation request to Gemini API")
            response = requests.post(url, json=data, timeout=45)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # Clean and parse the JSON response
                cleaned_text = self._clean_and_validate_json(response_text)
                if cleaned_text:
                    evaluation = json_lib.loads(cleaned_text)
                    
                    # Validate and normalize the score
                    score = float(evaluation.get('score', 0.0))
                    score = max(0.0, min(1.0, score))
                    
                    # Ensure all required fields are present
                    evaluation['score'] = round(score, 2)
                    evaluation['confidence'] = float(evaluation.get('confidence', 0.8))
                    evaluation['keywords_matched'] = evaluation.get('keywords_matched', [])
                    evaluation['improvement_suggestions'] = evaluation.get('improvement_suggestions', [])
                    evaluation['explanation'] = evaluation.get('explanation', 'Evaluation completed.')
                    evaluation['is_correct'] = evaluation.get('is_correct', score >= 0.6)
                    
                    logger.info(f"Voice evaluation completed. Score: {evaluation['score']}")
                    return evaluation
            
            # If API call fails, return error response
            logger.error("Gemini API failed for voice evaluation")
            return {
                "score": 0.5,
                "explanation": "Evaluation service temporarily unavailable.",
                "confidence": 0.5,
                "keywords_matched": [],
                "improvement_suggestions": ["Try again later"],
                "is_correct": False
            }
                
        except Exception as e:
            logger.error(f"Error in voice answer evaluation: {e}")
            # Return error response instead of fallback
            return {
                "score": 0.5,
                "explanation": "Evaluation service error.",
                "confidence": 0.3,
                "keywords_matched": [],
                "improvement_suggestions": ["Technical issue occurred during evaluation"],
                "is_correct": False
            }
    
    def _build_enhanced_voice_evaluation_prompt(self, question_text: str, model_answer: str, candidate_answer: str,
                                            work_profile: str, years_experience: int, difficulty_level: str) -> str:
        """
        Build a comprehensive prompt for accurate voice answer evaluation.
        This prompt specifically asks Gemini to compare the candidate answer with the expected answer.
        """
        return f"""
        You are an expert technical interviewer evaluating a candidate's response to an interview question.
        
        JOB PROFILE: {work_profile}
        EXPERIENCE LEVEL: {years_experience} years
        DIFFICULTY: {difficulty_level}
        
        INTERVIEW QUESTION: "{question_text}"
        
        CANDIDATE'S ANSWER: "{candidate_answer}"
        
        EXPECTED ANSWER / MODEL ANSWER: "{model_answer}"
        
        EVALUATION TASK:
        Compare the candidate's answer with the expected answer and provide a detailed evaluation.
        
        SCORING CRITERIA (0.0 to 1.0 scale):
        
        SCORE 0.9-1.0 (Excellent): 
        - Answer is comprehensive and covers all key points from the expected answer
        - Demonstrates deep understanding of the topic
        - Provides specific examples and technical details
        - Well-structured and clearly articulated
        
        SCORE 0.7-0.89 (Good):
        - Covers most key points from the expected answer
        - Shows good understanding but may miss some nuances
        - Generally accurate with minor omissions
        - Clear communication
        
        SCORE 0.5-0.69 (Satisfactory):
        - Covers basic concepts but misses important details
        - Some technical inaccuracies or oversimplifications
        - Lacks depth or specific examples
        - Partial understanding demonstrated
        
        SCORE 0.3-0.49 (Poor):
        - Misses major key points from expected answer
        - Significant technical inaccuracies
        - Very brief or vague response
        - Limited understanding demonstrated
        
        SCORE 0.1-0.29 (Very Poor):
        - Completely misses the point of the question
        - Major factual errors
        - Irrelevant or off-topic response
        
        SCORE 0.0 (Incorrect):
        - No meaningful response
        - "I don't know" without any attempt
        
        ADDITIONAL CONSIDERATIONS:
        - Reward technical accuracy and completeness
        - Penalize factual errors and significant omissions
        - Consider the experience level ({years_experience} years)
        - Evaluate based on how well the answer matches the expected answer content
        
        REQUIRED OUTPUT FORMAT (JSON only):
        {{
            "score": 0.85,
            "explanation": "Detailed analysis comparing candidate answer with expected answer. Highlight strengths, weaknesses, and specific areas of alignment/misalignment.",
            "confidence": 0.9,
            "keywords_matched": ["list", "of", "key", "technical", "terms", "from", "expected", "answer", "that", "appear", "in", "candidate", "answer"],
            "improvement_suggestions": ["specific suggestion 1", "specific suggestion 2", "specific suggestion 3"],
            "is_correct": true
        }}
        
        IMPORTANT: 
        - Be strict but fair in evaluation
        - The score should directly reflect how closely the candidate's answer matches the expected answer in content and accuracy
        - Provide specific, actionable feedback
        - List actual technical terms from the expected answer that appear in the candidate's answer
        """

    def _enhanced_fallback_evaluation(self, question_text: str, model_answer: str, candidate_answer: str) -> Dict[str, Any]:
        """
        Enhanced fallback evaluation with sophisticated answer analysis when Gemini fails.
        This uses multiple techniques to evaluate answer quality.
        """
        logger.info("Using ENHANCED fallback evaluation with multiple analysis techniques")
        
        candidate_answer_lower = candidate_answer.lower().strip()
        model_answer_lower = model_answer.lower()
        question_text_lower = question_text.lower()
        
        # Initialize analysis metrics
        analysis_metrics = {
            "word_count": len(candidate_answer.split()),
            "sentence_count": len([s for s in candidate_answer.split('.') if s.strip()]),
            "contains_technical_terms": False,
            "keyword_overlap": 0,
            "answer_relevance": 0,
            "specificity_score": 0
        }
        
        # Extract key technical terms from model answer
        technical_terms = self._extract_technical_terms(model_answer)
        question_keywords = self._extract_keywords(question_text)
        
        # Calculate keyword overlap between candidate answer and model answer
        matched_technical_terms = []
        for term in technical_terms:
            if term in candidate_answer_lower:
                matched_technical_terms.append(term)
                analysis_metrics["contains_technical_terms"] = True
        
        analysis_metrics["keyword_overlap"] = len(matched_technical_terms) / len(technical_terms) if technical_terms else 0
        
        # Calculate answer relevance to question
        question_terms_in_answer = sum(1 for term in question_keywords if term in candidate_answer_lower)
        analysis_metrics["answer_relevance"] = question_terms_in_answer / len(question_keywords) if question_keywords else 0
        
        # Calculate specificity score based on technical detail
        specificity_indicators = ['because', 'for example', 'specifically', 'in detail', 'technically', 
                                'architecture', 'implementation', 'framework', 'methodology']
        analysis_metrics["specificity_score"] = sum(1 for indicator in specificity_indicators if indicator in candidate_answer_lower) / len(specificity_indicators)
        
        # Calculate composite score using weighted metrics
        weights = {
            "word_count": 0.15,           # Length indicates effort
            "keyword_overlap": 0.35,      # Technical accuracy
            "answer_relevance": 0.25,     # Relevance to question
            "specificity_score": 0.25     # Depth of explanation
        }
        
        # Normalize word count score (optimal range 50-200 words)
        word_count_score = min(analysis_metrics["word_count"] / 100, 1.0) if analysis_metrics["word_count"] > 20 else analysis_metrics["word_count"] / 20
        
        composite_score = (
            weights["word_count"] * word_count_score +
            weights["keyword_overlap"] * analysis_metrics["keyword_overlap"] +
            weights["answer_relevance"] * analysis_metrics["answer_relevance"] +
            weights["specificity_score"] * analysis_metrics["specificity_score"]
        )
        
        # Adjust score based on answer quality indicators
        final_score = composite_score
        
        # Penalize very short answers
        if analysis_metrics["word_count"] < 15:
            final_score *= 0.3
        
        # Penalize answers with no technical terms
        if not analysis_metrics["contains_technical_terms"]:
            final_score *= 0.6
        
        # Ensure score is within bounds
        final_score = max(0.0, min(1.0, final_score))
        
        # Generate explanation based on score and analysis
        if final_score >= 0.8:
            explanation = "Excellent answer demonstrating strong understanding of the topic with good technical depth."
        elif final_score >= 0.6:
            explanation = "Good answer that covers key concepts but could use more technical detail or examples."
        elif final_score >= 0.4:
            explanation = "Satisfactory answer that addresses the topic at a basic level but lacks depth and technical accuracy."
        elif final_score >= 0.2:
            explanation = "Poor answer that shows limited understanding of the topic with significant gaps in knowledge."
        else:
            explanation = "Very poor answer that fails to address the question adequately."
        
        # Add technical feedback if applicable
        if matched_technical_terms:
            explanation += f" The answer correctly included technical terms like: {', '.join(matched_technical_terms[:3])}."
        
        # Generate improvement suggestions
        improvement_suggestions = self._generate_analytical_suggestions(final_score, analysis_metrics, matched_technical_terms, technical_terms)
        
        logger.info(f"Enhanced fallback evaluation completed. Score: {final_score}, Keywords matched: {len(matched_technical_terms)}")
        
        return {
            "score": round(final_score, 2),
            "explanation": explanation,
            "confidence": 0.7,  # Lower confidence for fallback
            "keywords_matched": matched_technical_terms,
            "improvement_suggestions": improvement_suggestions,
            "is_correct": final_score >= 0.6,
            "analysis_metrics": analysis_metrics  # Include for debugging
        }

    def _extract_technical_terms(self, text: str) -> List[str]:
        """
        Extract technical terms from text using sophisticated pattern matching.
        """
        if not text:
            return []
        
        # Common technical terms and patterns
        technical_patterns = [
            r'\b[A-Z][a-z]*(?:\s+[A-Z][a-z]*)*\b',  # Capitalized terms (likely proper nouns/technologies)
            r'\b\w*[A-Z]\w*\b',  # CamelCase or mixed case terms
        ]
        
        import re
        technical_terms = set()
        
        # Extract using patterns
        for pattern in technical_patterns:
            matches = re.findall(pattern, text)
            technical_terms.update(matches)
        
        # Filter out common non-technical terms
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                    'of', 'with', 'by', 'is', 'are', 'was', 'were', 'this', 'that', 'these', 'those'}
        
        # Additional filtering for meaningful technical terms
        filtered_terms = []
        for term in technical_terms:
            term_lower = term.lower()
            if (len(term) > 3 and 
                term_lower not in common_words and
                not term_lower.isnumeric() and
                any(c.isalpha() for c in term)):
                filtered_terms.append(term.lower())
        
        return list(set(filtered_terms))

    def _generate_analytical_suggestions(self, score: float, analysis_metrics: Dict, 
                                    matched_terms: List[str], all_technical_terms: List[str]) -> List[str]:
        """
        Generate highly specific improvement suggestions based on detailed analysis.
        """
        suggestions = []
        
        if score < 0.3:
            suggestions.extend([
                "Study the fundamental concepts related to this topic",
                "Practice articulating your thoughts more clearly and completely",
                "Research industry standards and best practices for this area"
            ])
        elif score < 0.6:
            suggestions.extend([
                "Provide more specific examples from your experience",
                "Include technical details about tools or methodologies used",
                "Explain the architecture or implementation approach more clearly"
            ])
            
            # Suggest missing technical terms
            missing_terms = [term for term in all_technical_terms if term not in matched_terms]
            if missing_terms and len(missing_terms) <= 5:
                suggestions.append(f"Consider including terms like: {', '.join(missing_terms[:3])}")
        
        elif score < 0.8:
            suggestions.extend([
                "Add more depth by discussing implementation challenges and solutions",
                "Include metrics or results that demonstrate impact",
                "Connect your answer to broader architectural patterns or principles"
            ])
        else:
            suggestions.extend([
                "Excellent answer! Consider adding more specific performance metrics",
                "You could discuss alternative approaches and why you chose your solution",
                "Consider mentioning how this approach scales in larger systems"
            ])
        
        # Add word count suggestions if applicable
        if analysis_metrics["word_count"] < 30:
            suggestions.append("Aim for more detailed explanations (50+ words for complex topics)")
        
        return suggestions[:4]  # Return top 4 suggestions
    
    def _improved_mock_evaluate_voice_answer(self, question_text: str, model_answer: str, candidate_answer: str) -> Dict[str, Any]:
        """
        Improved mock evaluation that provides realistic scores based on answer quality
        """
        logger.info("Using IMPROVED mock voice evaluation with realistic scoring")
        
        candidate_answer_lower = candidate_answer.lower().strip()
        question_text_lower = question_text.lower()
        
        # Analyze answer quality based on content
        word_count = len(candidate_answer.split())
        
        # Check for poor answers
        if (word_count < 10 or 
            "don't know" in candidate_answer_lower or 
            "no idea" in candidate_answer_lower or
            "not sure" in candidate_answer_lower or
            candidate_answer_lower in ["i don't know", "no", "nothing"]):
            score = random.uniform(0.1, 0.2)  # 10-20% for poor answers
            explanation = "The answer shows limited understanding or engagement with the question."
        
        # Check for very short or irrelevant answers
        elif word_count < 20:
            score = random.uniform(0.2, 0.4)  # 20-40% for very short answers
            explanation = "The answer is quite brief and lacks detail or depth."
        
        # Check for decent but basic answers
        elif word_count < 50:
            score = random.uniform(0.4, 0.7)  # 40-70% for basic answers
            explanation = "The answer addresses the question but could use more depth and specific examples."
        
        # Check for good detailed answers
        elif word_count < 100:
            score = random.uniform(0.7, 0.85)  # 70-85% for good answers
            explanation = "This is a good answer that shows understanding and provides relevant details."
        
        # Excellent detailed answers
        else:
            score = random.uniform(0.85, 0.95)  # 85-95% for excellent answers
            explanation = "Excellent detailed answer that thoroughly addresses the question with relevant examples and insights."
        
        # Adjust score based on specific keywords from the question
        question_keywords = self._extract_keywords(question_text)
        candidate_keywords = self._extract_keywords(candidate_answer)
        matched_keywords = [kw for kw in question_keywords if kw in candidate_answer_lower]
        
        if matched_keywords:
            keyword_bonus = min(len(matched_keywords) * 0.05, 0.15)  # Max 15% bonus
            score = min(score + keyword_bonus, 0.95)
            explanation += f" The answer includes relevant concepts like: {', '.join(matched_keywords[:3])}."
        
        # Generate appropriate improvement suggestions
        improvement_suggestions = self._generate_realistic_suggestions(score, word_count)
        
        return {
            "score": round(score, 2),
            "explanation": explanation,
            "confidence": 0.8,
            "keywords_matched": matched_keywords[:5],
            "improvement_suggestions": improvement_suggestions,
            "is_correct": score >= 0.6
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        if not text:
            return []
        
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
                     'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 
                     'this', 'that', 'these', 'those', 'what', 'which', 'how', 'when', 'where', 'why'}
        
        words = text.lower().split()
        keywords = [word.strip('.,!?;:()[]{}"\'') for word in words 
                   if word.strip('.,!?;:()[]{}"\'').isalpha() 
                   and word not in stop_words 
                   and len(word) > 3]
        
        return list(set(keywords))

    def _generate_realistic_suggestions(self, score: float, word_count: int) -> List[str]:
        """Generate realistic improvement suggestions based on score"""
        if score >= 0.8:
            return [
                "Excellent answer! Consider adding more specific metrics or results from your experience.",
                "You could mention how you measured the success of your approach."
            ]
        elif score >= 0.6:
            return [
                "Provide more specific examples from your experience",
                "Include technical details about tools or methodologies used",
                "Explain the impact or results of your actions"
            ]
        elif score >= 0.4:
            return [
                "Structure your answer with a clear beginning, middle, and end",
                "Provide more detailed explanations of your thought process",
                "Include specific technologies or tools you've worked with"
            ]
        else:
            return [
                "Study the fundamental concepts related to this question",
                "Practice articulating your thoughts more clearly and completely",
                "Prepare specific examples from your experience that relate to common interview questions"
            ]

    def generate_voice_interview_questions(self, profile: str, years_experience: int, 
                                    difficulty: str, n: int = 5) -> List[Dict[str, Any]]:
        """
        Generate voice interview questions using ONLY Gemini API - no fallback
        """
        try:
            prompt = f"""
            Generate {n} technical voice interview questions for a {profile} with {years_experience} years experience at {difficulty} level.
            
            Requirements:
            - Highly technical and specific to {profile} role
            - Appropriate difficulty for {difficulty} level
            - Focus on real-world scenarios and problem-solving
            - Each question should take 1-2 minutes to answer verbally
            
            Return ONLY valid JSON array in this format:
            [
                {{
                    "question": "Specific technical question...",
                    "model_answer": "Comprehensive technical answer..."
                }}
            ]
            """
            
            # Use direct HTTP API for Gemini
            api_key = "AIzaSyC4lfyxD20gaR5Pnji2aWUsw9ttM2S8eog"
            import requests
            import json as json_lib
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 4096,
                }
            }
            
            response = requests.post(url, json=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result['candidates'][0]['content']['parts'][0]['text']
                
                cleaned_text = self._clean_and_validate_json(response_text)
                if cleaned_text:
                    questions = json_lib.loads(cleaned_text)
                    return questions[:n]
            
            # If API fails, return empty list
            logger.error("Gemini API failed for voice question generation")
            return []
                
        except Exception as e:
            logger.error(f"Error generating voice questions: {e}")
            return []  # Return empty list instead of fallback

    def _create_voice_fallback_questions(self, profile: str, years_experience: int, difficulty: str, n: int) -> List[Dict[str, Any]]:
        """Create profile-specific voice questions"""
        questions = []
        base_scenarios = [
            f"Describe your approach to troubleshooting a complex technical issue as a {profile}",
            f"Explain how you would design a scalable solution for a common {profile} challenge",
            f"Walk through your technical decision-making process for selecting tools/technologies as a {profile}",
            f"Describe a technically complex project you worked on and the architecture decisions you made"
        ]
        
        for i in range(min(n, len(base_scenarios))):
            questions.append({
                "question": f"{base_scenarios[i]} considering {years_experience} years experience at {difficulty} level.",
                "model_answer": f"A comprehensive technical answer should demonstrate {difficulty}-level expertise in {profile} responsibilities, covering architecture, implementation, and best practices specific to this scenario."
            })
        
        return questions
