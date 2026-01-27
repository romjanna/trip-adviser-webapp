# Trip Adviser Web API

A Flask-based REST API for Trip Adviser, designed to run on Google Cloud Run with future mobile app support.

## Project Structure
```
.
├── app/
│   ├── __init__.py
│   └── main.py          # Main Flask application
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
├── .dockerignore        # Docker build exclusions
├── .gitignore          # Git exclusions
└── README.md           # This file
```

## Local Development

### Prerequisites
- Python 3.11+
- Docker (optional, for local container testing)

### Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally
python app/main.py
```

Access at: http://localhost:8080

## API Endpoints

- `GET /` - Health check
- `GET /api/health` - Detailed health check
- `GET /api/hello/<name>` - Example greeting endpoint

## Deployment

Deployed on Google Cloud Run in project: `trip-adviser-477323`

