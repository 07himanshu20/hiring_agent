# AI-Driven Hiring Agent

A complete Django application for conducting AI-powered hiring assessments with voice interview capabilities.

## Features

- **Round 1**: Automated written assessment with MCQ and short-answer questions
- **Round 2**: Voice interview with speech-to-text transcription and AI evaluation
- **AI Integration**: Gemini for question generation and answer evaluation
- **TTS/STT**: ElevenLabs for text-to-speech and Whisper for speech-to-text
- **Candidate Management**: Secure token-based access for candidates
- **Admin Dashboard**: Recruiter interface for creating roles and viewing results

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (optional)
- API keys for Gemini, ElevenLabs, and OpenAI (optional for mock mode)

### Environment Setup

1. Clone the repository and navigate to the project directory
2. Copy the environment template:
   ```bash
   cp .env.example .env