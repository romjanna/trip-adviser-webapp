"""
Pytest configuration and shared fixtures
"""
import os
import sys
import pytest
from io import BytesIO
from werkzeug.datastructures import FileStorage
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

from src.models import TranslationConfig
from src.translation_service import TranslationService

# Fixtures directory
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.fixture
def config():
    """Default TranslationConfig"""
    return TranslationConfig()


@pytest.fixture
def service(config):
    """TranslationService with real API key"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")
    return TranslationService(api_key=api_key, config=config)


@pytest.fixture
def audio_en():
    """English test audio fixture"""
    return _load_audio('test_audio_en.mp3')


@pytest.fixture
def audio_it():
    """Italian test audio fixture"""
    return _load_audio('test_audio_it.mp3')


@pytest.fixture
def audio_short():
    """Short test audio fixture"""
    return _load_audio('test_audio_short.mp3')


@pytest.fixture
def audio_long():
    """Long test audio fixture"""
    return _load_audio('test_audio_long.mp3')


def _load_audio(filename):
    """Helper to load audio file as FileStorage"""
    filepath = os.path.join(FIXTURES_DIR, filename)
    with open(filepath, 'rb') as f:
        audio_bytes = f.read()
    return FileStorage(
        stream=BytesIO(audio_bytes),
        filename=filename,
        content_type='audio/mpeg'
    )
