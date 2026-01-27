"""
Unit tests for data models
"""
import pytest
from src.models import LanguageCode, TranslationConfig, TranslationResult


class TestLanguageCode:
    """Tests for LanguageCode enum"""

    # Test from_name_or_code with ISO codes
    @pytest.mark.parametrize("code,expected", [
        ("en", LanguageCode.ENGLISH),
        ("it", LanguageCode.ITALIAN),
        ("es", LanguageCode.SPANISH),
        ("fr", LanguageCode.FRENCH),
        ("de", LanguageCode.GERMAN),
    ])
    def test_from_name_or_code_with_iso_codes(self, code, expected):
        assert LanguageCode.from_name_or_code(code) == expected

    # Test from_name_or_code with full names (as Whisper returns)
    @pytest.mark.parametrize("name,expected", [
        ("english", LanguageCode.ENGLISH),
        ("italian", LanguageCode.ITALIAN),
        ("spanish", LanguageCode.SPANISH),
        ("french", LanguageCode.FRENCH),
        ("german", LanguageCode.GERMAN),
    ])
    def test_from_name_or_code_with_full_names(self, name, expected):
        assert LanguageCode.from_name_or_code(name) == expected

    # Test case insensitivity
    @pytest.mark.parametrize("value,expected", [
        ("EN", LanguageCode.ENGLISH),
        ("English", LanguageCode.ENGLISH),
        ("ENGLISH", LanguageCode.ENGLISH),
        ("EnGlIsH", LanguageCode.ENGLISH),
    ])
    def test_from_name_or_code_case_insensitive(self, value, expected):
        assert LanguageCode.from_name_or_code(value) == expected

    # Test unsupported languages return None
    @pytest.mark.parametrize("value", [
        "ru",
        "russian",
        "chinese",
        "zh",
        "invalid",
        "",
    ])
    def test_from_name_or_code_unsupported_returns_none(self, value):
        assert LanguageCode.from_name_or_code(value) is None

    def test_get_supported_codes(self):
        codes = LanguageCode.get_supported_codes()
        assert codes == {"en", "it", "es", "fr", "de"}

    def test_code_property(self):
        assert LanguageCode.ENGLISH.code == "en"
        assert LanguageCode.ITALIAN.code == "it"

    def test_name_property(self):
        assert LanguageCode.ENGLISH.name == "English"
        assert LanguageCode.ITALIAN.name == "Italian"


class TestTranslationConfig:
    """Tests for TranslationConfig dataclass"""

    def test_default_values(self):
        config = TranslationConfig()
        assert config.MAX_FILE_SIZE_MB == 25
        assert config.MIN_TEXT_LENGTH == 3
        assert config.MAX_TEXT_LENGTH == 4096
        assert config.WHISPER_MODEL == "whisper-1"
        assert config.TTS_VOICE == "alloy"

    def test_allowed_formats_initialized(self):
        config = TranslationConfig()
        assert "audio/mpeg" in config.ALLOWED_FORMATS
        assert "audio/mp3" in config.ALLOWED_FORMATS
        assert "audio/wav" in config.ALLOWED_FORMATS

    def test_hallucination_keywords_initialized(self):
        config = TranslationConfig()
        assert "[inaudible]" in config.HALLUCINATION_KEYWORDS
        assert "subscribe" in config.HALLUCINATION_KEYWORDS

    def test_custom_values(self):
        config = TranslationConfig(
            MAX_FILE_SIZE_MB=10,
            MIN_TEXT_LENGTH=5,
            TTS_VOICE="nova"
        )
        assert config.MAX_FILE_SIZE_MB == 10
        assert config.MIN_TEXT_LENGTH == 5
        assert config.TTS_VOICE == "nova"


class TestTranslationResult:
    """Tests for TranslationResult dataclass"""

    def test_success_result(self):
        result = TranslationResult(
            success=True,
            audio_bytes=b"audio_data",
            original_text="Hello",
            translated_text="Ciao",
            detected_language="en",
            target_language="Italian"
        )
        assert result.success is True
        assert result.audio_bytes == b"audio_data"
        assert result.error_message is None
        assert result.hallucination_detected is False

    def test_failure_result(self):
        result = TranslationResult(
            success=False,
            error_message="Something went wrong",
            requires_retry=True
        )
        assert result.success is False
        assert result.error_message == "Something went wrong"
        assert result.requires_retry is True
        assert result.audio_bytes is None

    def test_hallucination_result(self):
        result = TranslationResult(
            success=False,
            error_message="Quality issue",
            hallucination_detected=True,
            original_text="Hello",
            translated_text="Subscribe to my channel"
        )
        assert result.hallucination_detected is True
        assert result.requires_retry is False  # default
