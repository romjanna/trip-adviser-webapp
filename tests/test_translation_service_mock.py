"""
Unit tests for TranslationService with mocked OpenAI API
These tests don't require an API key and run fast
"""
import pytest
from unittest.mock import Mock, patch
from io import BytesIO
from werkzeug.datastructures import FileStorage

from src.translation_service import TranslationService
from src.models import TranslationConfig, LanguageCode


@pytest.fixture
def service():
    """Create TranslationService with fake API key (mocked anyway)"""
    return TranslationService(api_key="fake-api-key", config=TranslationConfig())


@pytest.fixture
def mock_audio_file():
    """Create a mock audio file"""
    return FileStorage(
        stream=BytesIO(b"fake audio content"),
        filename="test.mp3",
        content_type="audio/mpeg"
    )


class TestGetTargetLanguage:
    """Tests for language pair logic (no API calls)"""

    def test_english_to_italian(self, service):
        assert service.get_target_language("en") == LanguageCode.ITALIAN

    def test_italian_to_english(self, service):
        assert service.get_target_language("it") == LanguageCode.ENGLISH

    def test_unsupported_defaults_to_english(self, service):
        assert service.get_target_language("es") == LanguageCode.ENGLISH
        assert service.get_target_language("fr") == LanguageCode.ENGLISH
        assert service.get_target_language("unknown") == LanguageCode.ENGLISH


class TestProcessTranslationMocked:
    """Tests for full translation pipeline with mocked OpenAI"""

    @patch.object(TranslationService, '_text_to_speech_with_retry')
    @patch.object(TranslationService, '_translate_with_retry')
    @patch.object(TranslationService, '_transcribe_with_retry')
    def test_successful_en_to_it_translation(
        self, mock_transcribe, mock_translate, mock_tts, service, mock_audio_file
    ):
        # Setup mocks
        mock_transcription = Mock()
        mock_transcription.text = "Hello, how are you today?"
        mock_transcription.language = "english"
        mock_transcribe.return_value = mock_transcription

        mock_translate.return_value = "Ciao, come stai oggi?"
        mock_tts.return_value = b"fake_audio_bytes"

        # Execute
        result = service.process_translation(mock_audio_file)

        # Assert
        assert result.success is True
        assert result.original_text == "Hello, how are you today?"
        assert result.translated_text == "Ciao, come stai oggi?"
        assert result.detected_language == "en"
        assert result.target_language == "Italian"
        assert result.audio_bytes == b"fake_audio_bytes"

        # Verify API was called correctly
        mock_transcribe.assert_called_once()
        mock_translate.assert_called_once_with(
            text="Hello, how are you today?",
            source_lang="en",
            target_lang="Italian"
        )
        mock_tts.assert_called_once_with("Ciao, come stai oggi?")

    @patch.object(TranslationService, '_text_to_speech_with_retry')
    @patch.object(TranslationService, '_translate_with_retry')
    @patch.object(TranslationService, '_transcribe_with_retry')
    def test_successful_it_to_en_translation(
        self, mock_transcribe, mock_translate, mock_tts, service, mock_audio_file
    ):
        # Setup mocks
        mock_transcription = Mock()
        mock_transcription.text = "Ciao, come stai?"
        mock_transcription.language = "italian"
        mock_transcribe.return_value = mock_transcription

        mock_translate.return_value = "Hello, how are you?"
        mock_tts.return_value = b"audio_data"

        # Execute
        result = service.process_translation(mock_audio_file)

        # Assert
        assert result.success is True
        assert result.detected_language == "it"
        assert result.target_language == "English"

    @patch.object(TranslationService, '_text_to_speech_with_retry')
    @patch.object(TranslationService, '_translate_with_retry')
    @patch.object(TranslationService, '_transcribe_with_retry')
    def test_unknown_language_defaults_to_english(
        self, mock_transcribe, mock_translate, mock_tts, service, mock_audio_file
    ):
        """Unknown languages default to English as source language"""
        mock_transcription = Mock()
        mock_transcription.text = "Привет мир, как дела?"
        mock_transcription.language = "russian"
        mock_transcribe.return_value = mock_transcription

        mock_translate.return_value = "Ciao mondo, come va?"
        mock_tts.return_value = b"audio"

        result = service.process_translation(mock_audio_file)

        # Unknown language defaults to English, translation proceeds
        assert result.success is True
        assert result.detected_language == "en"  # Defaulted to English

    @patch.object(TranslationService, '_transcribe_with_retry')
    def test_fails_on_text_too_short(
        self, mock_transcribe, service, mock_audio_file
    ):
        mock_transcription = Mock()
        mock_transcription.text = "Hi"
        mock_transcription.language = "english"
        mock_transcribe.return_value = mock_transcription

        result = service.process_translation(mock_audio_file)

        assert result.success is False
        assert "short" in result.error_message.lower()
        assert result.requires_retry is True

    @patch.object(TranslationService, '_translate_with_retry')
    @patch.object(TranslationService, '_transcribe_with_retry')
    def test_detects_hallucination_too_long(
        self, mock_transcribe, mock_translate, service, mock_audio_file
    ):
        mock_transcription = Mock()
        mock_transcription.text = "Hello world"
        mock_transcription.language = "english"
        mock_transcribe.return_value = mock_transcription

        # Translation way too long for input
        mock_translate.return_value = "Ciao mondo " * 20

        result = service.process_translation(mock_audio_file)

        assert result.success is False
        assert result.hallucination_detected is True

    @patch.object(TranslationService, '_translate_with_retry')
    @patch.object(TranslationService, '_transcribe_with_retry')
    def test_detects_hallucination_keyword(
        self, mock_transcribe, mock_translate, service, mock_audio_file
    ):
        mock_transcription = Mock()
        mock_transcription.text = "Hello, this is a test message for translation"
        mock_transcription.language = "english"
        mock_transcribe.return_value = mock_transcription

        # Translation contains hallucination keyword
        mock_translate.return_value = "Ciao, please subscribe to my channel"

        result = service.process_translation(mock_audio_file)

        assert result.success is False
        assert result.hallucination_detected is True

    def test_fails_on_empty_file(self, service):
        empty_file = FileStorage(
            stream=BytesIO(b""),
            filename="test.mp3",
            content_type="audio/mpeg"
        )

        result = service.process_translation(empty_file)

        assert result.success is False
        assert "empty" in result.error_message.lower()

    def test_fails_on_invalid_format(self, service):
        invalid_file = FileStorage(
            stream=BytesIO(b"fake content"),
            filename="test.txt",
            content_type="text/plain"
        )

        result = service.process_translation(invalid_file)

        assert result.success is False


class TestLanguageNormalization:
    """Tests for Whisper language format handling"""

    @patch.object(TranslationService, '_text_to_speech_with_retry')
    @patch.object(TranslationService, '_translate_with_retry')
    @patch.object(TranslationService, '_transcribe_with_retry')
    @pytest.mark.parametrize("whisper_lang,expected_code", [
        ("english", "en"),
        ("English", "en"),
        ("ENGLISH", "en"),
        ("en", "en"),
        ("italian", "it"),
        ("Italian", "it"),
        ("it", "it"),
    ])
    def test_normalizes_whisper_language_format(
        self, mock_transcribe, mock_translate, mock_tts,
        service, mock_audio_file, whisper_lang, expected_code
    ):
        mock_transcription = Mock()
        mock_transcription.text = "Test message for translation"
        mock_transcription.language = whisper_lang
        mock_transcribe.return_value = mock_transcription

        mock_translate.return_value = "Translated message"
        mock_tts.return_value = b"audio"

        result = service.process_translation(mock_audio_file)

        assert result.success is True
        assert result.detected_language == expected_code
