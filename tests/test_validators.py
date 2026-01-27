"""
Unit tests for validators
"""
import pytest
from io import BytesIO
from werkzeug.datastructures import FileStorage

from src.models import TranslationConfig
from src.validators import TranslationValidator, AudioFileValidator


class TestTranslationValidator:
    """Tests for TranslationValidator"""

    @pytest.fixture
    def validator(self):
        return TranslationValidator(TranslationConfig())

    # Text length validation tests
    def test_validate_text_length_valid(self, validator):
        is_valid, error = validator.validate_text_length("Hello, this is a test")
        assert is_valid is True
        assert error is None

    def test_validate_text_length_too_short(self, validator):
        is_valid, error = validator.validate_text_length("Hi")
        assert is_valid is False
        assert "too short" in error.lower()

    def test_validate_text_length_empty(self, validator):
        is_valid, error = validator.validate_text_length("")
        assert is_valid is False
        assert "too short" in error.lower()

    def test_validate_text_length_whitespace_only(self, validator):
        is_valid, error = validator.validate_text_length("   ")
        assert is_valid is False

    def test_validate_text_length_too_long(self, validator):
        long_text = "a" * 5000
        is_valid, error = validator.validate_text_length(long_text)
        assert is_valid is False
        assert "maximum length" in error.lower()

    def test_validate_text_length_at_minimum(self, validator):
        is_valid, error = validator.validate_text_length("Hey")  # 3 chars
        assert is_valid is True

    # Language detection validation tests
    def test_validate_language_detection_supported(self, validator):
        is_valid, error = validator.validate_language_detection("en")
        assert is_valid is True
        assert error is None

    def test_validate_language_detection_unsupported(self, validator):
        is_valid, error = validator.validate_language_detection("ru")
        assert is_valid is False
        assert "unsupported" in error.lower()

    def test_validate_language_detection_low_confidence(self, validator):
        is_valid, error = validator.validate_language_detection("en", confidence=0.5)
        assert is_valid is False
        assert "confidence" in error.lower()

    def test_validate_language_detection_high_confidence(self, validator):
        is_valid, error = validator.validate_language_detection("en", confidence=0.9)
        assert is_valid is True

    # Hallucination detection tests
    def test_check_hallucination_valid_translation(self, validator):
        is_hallucination, reason = validator.check_hallucination(
            original_text="Hello, how are you?",
            translated_text="Ciao, come stai?",
            detected_language="en"
        )
        assert is_hallucination is False
        assert reason is None

    def test_check_hallucination_too_long(self, validator):
        is_hallucination, reason = validator.check_hallucination(
            original_text="Hi",
            translated_text="This is a very long translation that should not exist for such a short input",
            detected_language="en"
        )
        assert is_hallucination is True
        assert "long" in reason.lower()

    def test_check_hallucination_too_short(self, validator):
        is_hallucination, reason = validator.check_hallucination(
            original_text="Hello, this is a long sentence that needs proper translation",
            translated_text="Hi",
            detected_language="en"
        )
        assert is_hallucination is True
        assert "short" in reason.lower()

    def test_check_hallucination_keyword_detected(self, validator):
        is_hallucination, reason = validator.check_hallucination(
            original_text="Hello world, how are you today my friend",
            translated_text="Ciao mondo, please subscribe to my channel",
            detected_language="en"
        )
        assert is_hallucination is True
        assert "keyword" in reason.lower()

    def test_check_hallucination_identical_text(self, validator):
        text = "This is a test sentence that is long enough"
        is_hallucination, reason = validator.check_hallucination(
            original_text=text,
            translated_text=text,
            detected_language="en"
        )
        assert is_hallucination is True
        assert "identical" in reason.lower()

    def test_check_hallucination_excessive_repetition(self, validator):
        is_hallucination, reason = validator.check_hallucination(
            original_text="Please translate this",
            translated_text="word word word word word word word word",
            detected_language="en"
        )
        assert is_hallucination is True
        assert "repetition" in reason.lower()


class TestAudioFileValidator:
    """Tests for AudioFileValidator"""

    @pytest.fixture
    def validator(self):
        return AudioFileValidator(TranslationConfig())

    def _create_file_storage(self, content=b"fake audio content",
                              filename="test.mp3",
                              content_type="audio/mpeg"):
        return FileStorage(
            stream=BytesIO(content),
            filename=filename,
            content_type=content_type
        )

    def test_validate_valid_mp3(self, validator):
        audio_file = self._create_file_storage()
        is_valid, error = validator.validate(audio_file)
        assert is_valid is True
        assert error is None

    def test_validate_valid_wav(self, validator):
        audio_file = self._create_file_storage(
            filename="test.wav",
            content_type="audio/wav"
        )
        is_valid, error = validator.validate(audio_file)
        assert is_valid is True

    def test_validate_no_file(self, validator):
        is_valid, error = validator.validate(None)
        assert is_valid is False
        assert "no audio file" in error.lower()

    def test_validate_empty_filename(self, validator):
        audio_file = self._create_file_storage(filename="")
        is_valid, error = validator.validate(audio_file)
        assert is_valid is False

    def test_validate_unsupported_content_type(self, validator):
        audio_file = self._create_file_storage(content_type="video/mp4")
        is_valid, error = validator.validate(audio_file)
        assert is_valid is False
        assert "unsupported format" in error.lower()

    def test_validate_empty_file(self, validator):
        audio_file = self._create_file_storage(content=b"")
        is_valid, error = validator.validate(audio_file)
        assert is_valid is False
        assert "empty" in error.lower()

    def test_validate_file_too_large(self, validator):
        # Create config with small max size for testing
        config = TranslationConfig(MAX_FILE_SIZE_MB=1)
        validator = AudioFileValidator(config)

        # Create file larger than 1MB
        large_content = b"x" * (2 * 1024 * 1024)  # 2MB
        audio_file = self._create_file_storage(content=large_content)

        is_valid, error = validator.validate(audio_file)
        assert is_valid is False
        assert "too large" in error.lower()

    def test_validate_invalid_extension(self, validator):
        audio_file = self._create_file_storage(
            filename="test.txt",
            content_type="audio/mpeg"
        )
        is_valid, error = validator.validate(audio_file)
        assert is_valid is False
        assert "extension" in error.lower()

    def test_get_file_hash(self, validator):
        content = b"test audio content"
        audio_file = self._create_file_storage(content=content)

        hash1 = validator.get_file_hash(audio_file)
        hash2 = validator.get_file_hash(audio_file)

        assert hash1 == hash2  # Same content = same hash
        assert len(hash1) == 32  # MD5 hash length
