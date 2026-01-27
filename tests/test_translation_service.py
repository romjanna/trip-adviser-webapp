"""
Integration tests for TranslationService using real audio fixtures
"""
import pytest
from src.models import LanguageCode


@pytest.mark.integration
class TestTranslationServiceWithRealAudio:
    """Integration tests using real audio fixtures"""

    def test_english_to_italian_translation(self, service, audio_en):
        """Test EN -> IT translation with test_audio_en.mp3"""
        result = service.process_translation(audio_en)

        assert result.success is True
        assert result.original_text is not None
        assert result.translated_text is not None
        assert result.detected_language == "en"
        assert result.target_language == "Italian"
        assert result.audio_bytes is not None
        assert len(result.audio_bytes) > 0
        print(f"\nEN -> IT:")
        print(f"  Original: {result.original_text}")
        print(f"  Translated: {result.translated_text}")

    def test_italian_to_english_translation(self, service, audio_it):
        """Test IT -> EN translation with test_audio_it.mp3"""
        result = service.process_translation(audio_it)

        assert result.success is True
        assert result.original_text is not None
        assert result.translated_text is not None
        assert result.detected_language == "it"
        assert result.target_language == "English"
        assert result.audio_bytes is not None
        print(f"\nIT -> EN:")
        print(f"  Original: {result.original_text}")
        print(f"  Translated: {result.translated_text}")

    def test_short_audio_fails_validation(self, service, audio_short):
        """Test that short audio (just 'Hi') fails text length validation"""
        result = service.process_translation(audio_short)

        # Short text should fail validation
        assert result.success is False
        assert result.requires_retry is True
        print(f"\nShort audio result: {result.error_message}")

    def test_long_audio_translation(self, service, audio_long):
        """Test long audio translation with test_audio_long.mp3"""
        result = service.process_translation(audio_long)

        # Long audio should either succeed or fail with hallucination detection
        if result.success:
            assert result.translated_text is not None
            print(f"\nLong audio succeeded:")
            print(f"  Original length: {len(result.original_text)}")
            print(f"  Translated length: {len(result.translated_text)}")
        else:
            # May fail due to repetition detection (hallucination)
            print(f"\nLong audio failed: {result.error_message}")
            assert result.error_message is not None

    def test_english_to_italian_contains_expected_words(self, service, audio_en):
        """Test that EN -> IT translation contains expected Italian words

        test_audio_en.mp3 says: "Hello, my name is Mira. I would like to order
        a pizza with mushrooms and cheese. Thank you very much!"
        """
        result = service.process_translation(audio_en)

        assert result.success is True
        translated_lower = result.translated_text.lower()

        # Should contain at least some of these Italian words/names
        expected_words = ["mira", "pizza", "funghi", "formaggio", "grazie"]
        found_words = [w for w in expected_words if w in translated_lower]

        print(f"\nExpected words found: {found_words}")
        assert len(found_words) >= 2, f"Translation should contain Italian words. Got: {result.translated_text}"

    def test_italian_to_english_contains_expected_words(self, service, audio_it):
        """Test that IT -> EN translation contains expected English words

        test_audio_it.mp3 says: "Buongiorno, mi chiamo Emanuel. Vorrei prenotare
        un tavolo per due persone stasera alle otto. Grazie mille!"
        """
        result = service.process_translation(audio_it)

        assert result.success is True
        translated_lower = result.translated_text.lower()

        # Should contain at least some of these English words/names
        # Note: "Emanuel" may be transcribed as "Emmanuel" by Whisper
        expected_words = ["emanuel", "emmanuel", "table", "two", "eight", "thank", "evening", "book", "reserve"]
        found_words = [w for w in expected_words if w in translated_lower]

        print(f"\nExpected words found: {found_words}")
        assert len(found_words) >= 2, f"Translation should contain English words. Got: {result.translated_text}"


class TestLanguageDetection:
    """Tests for language detection and normalization"""

    def test_get_target_language_english(self, service):
        target = service.get_target_language("en")
        assert target == LanguageCode.ITALIAN

    def test_get_target_language_italian(self, service):
        target = service.get_target_language("it")
        assert target == LanguageCode.ENGLISH

    def test_get_target_language_unsupported_defaults_english(self, service):
        target = service.get_target_language("es")
        assert target == LanguageCode.ENGLISH


class TestLanguageCodeNormalization:
    """Tests for LanguageCode.from_name_or_code (the bug fix)"""

    @pytest.mark.parametrize("input_value,expected", [
        # ISO codes
        ("en", LanguageCode.ENGLISH),
        ("it", LanguageCode.ITALIAN),
        # Full names (as Whisper returns)
        ("english", LanguageCode.ENGLISH),
        ("italian", LanguageCode.ITALIAN),
        # Case variations
        ("English", LanguageCode.ENGLISH),
        ("ENGLISH", LanguageCode.ENGLISH),
        ("Italian", LanguageCode.ITALIAN),
    ])
    def test_from_name_or_code(self, input_value, expected):
        result = LanguageCode.from_name_or_code(input_value)
        assert result == expected

    @pytest.mark.parametrize("input_value", [
        "russian",
        "ru",
        "chinese",
        "unknown",
    ])
    def test_from_name_or_code_unsupported(self, input_value):
        result = LanguageCode.from_name_or_code(input_value)
        assert result is None
