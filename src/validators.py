"""
Validation classes for audio files and translation quality
"""
import os
import hashlib
import logging
from typing import Tuple, Optional
from werkzeug.datastructures import FileStorage

from .models import TranslationConfig, LanguageCode

logger = logging.getLogger(__name__)


class TranslationValidator:
    """Validates translation quality and detects hallucinations"""
    
    def __init__(self, config: TranslationConfig):
        self.config = config
    
    def validate_text_length(self, text: str) -> Tuple[bool, Optional[str]]:
        """Validate text length is within acceptable range"""
        if not text or len(text.strip()) < self.config.MIN_TEXT_LENGTH:
            return False, "Text too short or empty"
        
        if len(text) > self.config.MAX_TEXT_LENGTH:
            return False, f"Text exceeds maximum length of {self.config.MAX_TEXT_LENGTH} characters"
        
        return True, None
    
    def check_hallucination(
        self,
        original_text: str,
        translated_text: str,
        detected_language: str
    ) -> Tuple[bool, Optional[str]]:
        """Detect potential hallucinations in translation"""
        
        original_len = len(original_text.strip())
        translated_len = len(translated_text.strip())
        
        # Check 1: Length ratio validation
        if original_len > 0:
            length_ratio = translated_len / original_len
            
            if length_ratio > self.config.MAX_LENGTH_RATIO:
                return True, f"Translation suspiciously long (ratio: {length_ratio:.2f})"
            
            if length_ratio < self.config.MIN_LENGTH_RATIO:
                return True, f"Translation suspiciously short (ratio: {length_ratio:.2f})"
        
        # Check 2: Hallucination keyword detection
        translated_lower = translated_text.lower()
        for keyword in self.config.HALLUCINATION_KEYWORDS:
            if keyword.lower() in translated_lower:
                return True, f"Hallucination keyword detected: '{keyword}'"
        
        # Check 3: Check if translation is identical to original
        if original_len > 20 and original_text.strip().lower() == translated_text.strip().lower():
            return True, "Translation identical to original"
        
        # Check 4: Detect excessive repetition
        words = translated_text.split()
        if len(words) > 5:
            trigrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
            unique_trigrams = set(trigrams)
            if len(unique_trigrams) < len(trigrams) * 0.7:
                return True, "Excessive repetition detected"
        
        return False, None
    
    def validate_language_detection(
        self,
        detected_language: str,
        confidence: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """Validate detected language is supported"""
        
        if detected_language not in LanguageCode.get_supported_codes():
            return False, f"Unsupported language detected: {detected_language}"
        
        if confidence is not None and confidence < self.config.MIN_CONFIDENCE_SCORE:
            return False, f"Low confidence: {confidence:.2f}"
        
        return True, None


class AudioFileValidator:
    """Validates audio file before processing"""
    
    def __init__(self, config: TranslationConfig):
        self.config = config
    
    def validate(self, audio_file: FileStorage) -> Tuple[bool, Optional[str]]:
        """Comprehensive audio file validation"""
        
        if not audio_file or audio_file.filename == '':
            return False, "No audio file provided"
        
        if audio_file.content_type not in self.config.ALLOWED_FORMATS:
            return False, f"Unsupported format: {audio_file.content_type}"
        
        # File size validation
        audio_file.seek(0, os.SEEK_END)
        file_size = audio_file.tell()
        audio_file.seek(0)
        
        max_size_bytes = self.config.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"File too large: {file_size/1024/1024:.2f}MB"
        
        if file_size == 0:
            return False, "Audio file is empty"
        
        # Extension validation
        allowed_extensions = {'.mp3', '.wav', '.m4a', '.webm', '.ogg', '.flac'}
        file_ext = os.path.splitext(audio_file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return False, f"Invalid extension: {file_ext}"
        
        return True, None
    
    def get_file_hash(self, audio_file: FileStorage) -> str:
        """Generate hash for file deduplication"""
        audio_file.seek(0)
        file_hash = hashlib.md5(audio_file.read()).hexdigest()
        audio_file.seek(0)
        return file_hash
