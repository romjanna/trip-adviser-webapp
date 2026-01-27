"""
Flask application entry point for Cloud Run
"""
import logging
import sys
import os

# Load environment variables from .env file (for local development)
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, make_response, jsonify
from flask_cors import CORS

from src.config import Config
from src.translation_service import TranslationService
from src.models import TranslationConfig

# Initialize configuration
try:
    config = Config.from_env()
except ValueError as e:
    # For local development without proper config
    print(f"Config error: {e}")
    print("Please check your .env file")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=config.CORS_ORIGINS)


@app.route('/')
def home():
    """Home endpoint"""
    return jsonify({
        'status': 'success',
        'message': 'Translation API is running',
        'version': '1.0.0',
        'environment': config.ENV.value
    })


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({
        "status": "healthy",
        "service": "translation-api",
        "environment": config.ENV.value
    }), 200


@app.route('/translate', methods=['POST'])
def translate():
    """Main translation endpoint"""
    
    try:
        # Check for audio file
        if 'audio' not in request.files:
            logger.warning("No audio file in request")
            return make_response(
                jsonify({"error": "No audio file provided"}),
                400
            )
        
        audio_file = request.files['audio']
        
        # Initialize service
        translation_config = TranslationConfig(
            MAX_FILE_SIZE_MB=config.MAX_FILE_SIZE_MB,
            MIN_CONFIDENCE_SCORE=config.MIN_CONFIDENCE_SCORE,
            MAX_RETRIES=config.MAX_RETRIES
        )
        
        service = TranslationService(
            api_key=config.OPENAI_API_KEY,
            config=translation_config
        )
        
        # Process translation
        result = service.process_translation(audio_file)
        
        # Handle errors
        if not result.success:
            status_code = 400 if result.requires_retry else 500
            response_data = {
                "error": result.error_message,
                "requires_retry": result.requires_retry,
                "hallucination_detected": result.hallucination_detected
            }
            
            if result.detected_language:
                response_data["detected_language"] = result.detected_language
            if result.original_text:
                response_data["original_text"] = result.original_text
            
            return make_response(jsonify(response_data), status_code)
        
        # Success - return audio with metadata
        response = make_response(result.audio_bytes)
        response.headers['Content-Type'] = 'audio/mpeg'
        response.headers['Content-Disposition'] = 'attachment; filename=translated.mp3'
        response.headers['X-Original-Text'] = result.original_text
        response.headers['X-Translated-Text'] = result.translated_text
        response.headers['X-Detected-Language'] = result.detected_language
        response.headers['X-Target-Language'] = result.target_language
        
        return response
    
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return make_response(
            jsonify({"error": "Internal server error"}),
            500
        )


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    # For local development only
    logger.info(f"Starting Translation API in {config.ENV.value} mode")
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )
