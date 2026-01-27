# Bilingual Translation API

A Flask-based REST API for audio translation between English and Italian, powered by OpenAI. Designed to run on Google Cloud Run.

## Features

- Audio transcription using OpenAI Whisper
- Bidirectional translation (English ↔ Italian)
- Text-to-speech output
- Hallucination detection
- Comprehensive test suite

## Project Structure
```
.
├── app/
│   └── main.py              # Flask application entry point
├── src/
│   ├── config.py            # Configuration management
│   ├── models.py            # Data models (LanguageCode, TranslationConfig, etc.)
│   ├── translation_service.py  # Core translation logic
│   └── validators.py        # Input validation and hallucination detection
├── tests/
│   ├── fixtures/            # Test audio files
│   ├── test_models.py       # Unit tests for models
│   ├── test_validators.py   # Unit tests for validators
│   ├── test_translation_service.py       # Integration tests (requires API key)
│   └── test_translation_service_mock.py  # Unit tests with mocked API
├── requirements.txt
├── pytest.ini
└── README.md
```

## Local Development

### Prerequisites
- Python 3.11+
- OpenAI API key

### Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run locally
python app/main.py
```

Access at: http://localhost:8080

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API status |
| `/health` | GET | Health check |
| `/translate` | POST | Translate audio file |

### Translation Endpoint

**Request:**
```bash
curl -X POST -F "audio=@your_audio.mp3;type=audio/mpeg" http://localhost:8080/translate --output translated.mp3
```

**Response Headers:**
- `X-Original-Text` - Transcribed text
- `X-Translated-Text` - Translated text
- `X-Detected-Language` - Source language (en/it)
- `X-Target-Language` - Target language (English/Italian)

**Response Body:** MP3 audio file

## Testing

```bash
# Run all unit tests (no API key needed)
pytest tests/ -m "not integration" -v

# Run all tests including integration (requires API key)
pytest tests/ -v

# Run with output
pytest tests/ -v -s
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `ENV` | No | development | Environment (development/staging/production) |
| `PORT` | No | 8080 | Server port |
| `HOST` | No | 0.0.0.0 | Server host |
| `LOG_LEVEL` | No | INFO | Logging level |

## Deployment

Deployed on Google Cloud Run in project: `trip-adviser-477323`

### Deploy to Cloud Run
```bash
gcloud run deploy translation-api \
  --source . \
  --region europe-west1 \
  --set-env-vars OPENAI_API_KEY=your-key
```
