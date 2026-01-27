"""
Data models and enumerations for translation service
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class LanguageCode(Enum):
    """Supported language codes with their full names"""
    ENGLISH = ("en", "English")
    ITALIAN = ("it", "Italian")
    SPANISH = ("es", "Spanish")
    FRENCH = ("fr", "French")
    GERMAN = ("de", "German")
    
    @property
    def code(self) -> str:
        return self.value[0]
    
    @property
    def name(self) -> str:
        return self.value[1]
    
    @classmethod
    def from_code(cls, code: str) -> Optional['LanguageCode']:
        """Get LanguageCode from ISO code"""
        for lang in cls:
            if lang.code == code.lower():
                return lang
        return None
    
    @classmethod
    def get_supported_codes(cls) -> set:
        """Get set of supported language codes"""
        return {lang.code for lang in cls}


@dataclass
class TranslationConfig:
    """Configuration for translation service"""
    # File validation
    MAX_FILE_SIZE_MB: int = 25
    ALLOWED_FORMATS: set = None
    MAX_DURATION_SECONDS: int = 600
    
    # Detection thresholds
    MIN_CONFIDENCE_SCORE: float = 0.7
    MIN_TEXT_LENGTH: int = 3
    MAX_TEXT_LENGTH: int = 4096
    
    # Hallucination detection
    MAX_LENGTH_RATIO: float = 3.0
    MIN_LENGTH_RATIO: float = 0.3
    HALLUCINATION_KEYWORDS: set = None
    
    # API configuration
    WHISPER_MODEL: str = "whisper-1"
    TRANSLATION_MODEL: str = "gpt-4o-mini"
    TTS_MODEL: str = "tts-1"
    TTS_VOICE: str = "alloy"
    
    # Retry configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1
    
    def __post_init__(self):
        if self.ALLOWED_FORMATS is None:
            self.ALLOWED_FORMATS = {
                'audio/mpeg', 'audio/mp3', 'audio/wav',
                'audio/m4a', 'audio/webm', 'audio/ogg'
            }
        if self.HALLUCINATION_KEYWORDS is None:
            self.HALLUCINATION_KEYWORDS = {
                '[inaudible]', '[music]', '[noise]',
                'subscribe', 'like and subscribe',
                'thank you for watching', 'please subscribe'
            }


@dataclass
class TranslationResult:
    """Result of translation operation"""
    success: bool
    audio_bytes: Optional[bytes] = None
    original_text: Optional[str] = None
    translated_text: Optional[str] = None
    detected_language: Optional[str] = None
    target_language: Optional[str] = None
    confidence_score: Optional[float] = None
    error_message: Optional[str] = None
    requires_retry: bool = False
    hallucination_detected: bool = False
