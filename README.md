# Personal Tutor Backend

A Python FastAPI backend for a personal tutor application where students can upload handwritten notes, receive feedback, and get personalized question suggestions.

## Features

- User authentication and profile management
- Handwritten note upload and management
- Question and feedback system
- Learning analytics and weak area tracking
- Suggested questions generation (LLM integration ready)

## Tech Stack

- **Backend**: Python with FastAPI
- **Database**: MongoDB
- **File Storage**: Cloudinary
- **Authentication**: JWT tokens
- **Image Processing**: Pillow

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env` file

3. Run MongoDB locally or use MongoDB Atlas

4. Start the server:
```bash
uvicorn app.main:app --reload
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
personal_tutor_backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── models/              # Pydantic models
│   ├── routers/             # API route handlers
│   ├── utils/               # Utility functions
│   └── core/                # Core configuration and security
├── requirements.txt
├── .env
└── README.md
```
