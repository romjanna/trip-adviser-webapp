"""
Core translation service with OpenAI integration
"""
import logging
from typing import Tuple, Optional, Any
from openai import OpenAI, OpenAIError
from werkzeug.datastructures import FileStorage
import tenacity

from .models import (
    TranslationConfig,
    TranslationResult,
    LanguageCode
)
from .validators import TranslationValidator, AudioFileValidator

logger = logging.getLogger(__name__)                                                                                              

class TranslationService:
    """Core translation service with enterprise features"""
    
    def __init__(self, api_key: str, config: Optional[TranslationConfig] = None):
        self.client = OpenAI(api_key=api_key)
        self.config = config or TranslationConfig()
        self.validator = TranslationValidator(self.config)
        self.file_validator = AudioFileValidator(self.config)
        
        # Language pair mapping for bidirectional translation
        self.language_pairs = {
            LanguageCode.ENGLISH.code: LanguageCode.ITALIAN,
            LanguageCode.ITALIAN.code: LanguageCode.ENGLISH,
        }
    
    def get_target_language(self, detected_code: str) -> LanguageCode:
        """Determine target language for bidirectional translation"""
        target = self.language_pairs.get(detected_code)
        if target:
            return target
        
        logger.warning(f"No pair for {detected_code}, defaulting to English")
        return LanguageCode.ENGLISH
    
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type((OpenAIError, ConnectionError)),
        before_sleep=lambda retry_state: logger.info(f"Retrying transcription, attempt {retry_state.attempt_number}")
    )
    def _transcribe_with_retry(self, audio_data: Tuple) -> Any:
        """Transcribe audio with retry logic"""
        return self.client.audio.transcriptions.create(
            model=self.config.WHISPER_MODEL,
            file=audio_data,
            response_format="verbose_json"
        )
    
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type((OpenAIError, ConnectionError)),
        before_sleep=lambda retry_state: logger.info(f"Retrying translation, attempt {retry_state.attempt_number}")
    )
    def _translate_with_retry(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """Translate text with retry and hallucination prevention"""
        
        system_prompt = f"""You are a professional translator. Translate from {source_lang} to {target_lang}.

RULES:
1. Translate ONLY the provided text
2. No explanations or commentary
3. No added content
4. Preserve tone and style
5. Provide ONLY the translation"""

        response = self.client.chat.completions.create(
            model=self.config.TRANSLATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=len(text) * 3,
        )
        
        return response.choices[0].message.content.strip()
    
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type((OpenAIError, ConnectionError)),
        before_sleep=lambda retry_state: logger.info(f"Retrying TTS, attempt {retry_state.attempt_number}")
    )
    def _text_to_speech_with_retry(self, text: str) -> bytes:
        """Convert text to speech with retry"""
        response = self.client.audio.speech.create(
            model=self.config.TTS_MODEL,
            voice=self.config.TTS_VOICE,
            input=text
        )
        return response.content
    
    def process_translation(self, audio_file: FileStorage) -> TranslationResult:
        """Main translation pipeline"""
        
        try:
            # Step 1: Validate audio file
            logger.info(f"Processing: {audio_file.filename}")
            is_valid, error_msg = self.file_validator.validate(audio_file)
            if not is_valid:
                logger.error(f"Validation failed: {error_msg}")
                return TranslationResult(success=False, error_message=error_msg)
            
            # Step 2: Transcribe
            audio_file.seek(0)
            audio_data = (
                audio_file.filename,
                audio_file.read(),
                audio_file.content_type
            )
            
            logger.info("Transcribing...")
            transcription = self._transcribe_with_retry(audio_data)
            
            original_text = transcription.text.strip()
            detected_language = transcription.language                                                       
            lang_enum = LanguageCode.from_name_or_code(detected_language)                                    
            if lang_enum:                                                                                    
                detected_language = lang_enum.code  # Normalize to ISO code
            else:
                logger.warning(f"Unknown language: {detected_language}, using English")
                detected_language = LanguageCode.ENGLISH.code
                
            logger.info(f"Detected language for transcription: {detected_language}, Length: {len(original_text)}")
            # Step 3: Validate transcription
            is_valid, error_msg = self.validator.validate_text_length(original_text)
            if not is_valid:
                return TranslationResult(
                    success=False,
                    error_message=f"{error_msg}. Please speak clearly.",
                    detected_language=detected_language,
                    original_text=original_text,
                    requires_retry=True
                )
            
            # Step 4: Validate language
            is_valid, error_msg = self.validator.validate_language_detection(detected_language)
            if not is_valid:
                return TranslationResult(
                    success=False,
                    error_message=f"{error_msg}. Supported: English, Italian.",
                    detected_language=detected_language,
                    original_text=original_text,
                    requires_retry=True
                )
            
            # Step 5: Determine target
            target_lang_enum = self.get_target_language(detected_language)
            target_lang_name = target_lang_enum.name
            
            logger.info(f"Translating: {detected_language} -> {target_lang_enum.code}")
            
            # Step 6: Translate
            translated_text = self._translate_with_retry(
                text=original_text,
                source_lang=detected_language,
                target_lang=target_lang_name
            )
            
            logger.info(f"Translation complete: {len(translated_text)} chars")
            
            # Step 7: Check hallucination
            is_hallucination, reason = self.validator.check_hallucination(
                original_text=original_text,
                translated_text=translated_text,
                detected_language=detected_language
            )
            
            if is_hallucination:
                logger.warning(f"Hallucination: {reason}")
                return TranslationResult(
                    success=False,
                    error_message=f"Quality issue: {reason}. Try again.",
                    original_text=original_text,
                    translated_text=translated_text,
                    detected_language=detected_language,
                    target_language=target_lang_name,
                    requires_retry=True,
                    hallucination_detected=True
                )
            
            # Step 8: Text-to-speech
            logger.info("Converting to speech...")
            audio_bytes = self._text_to_speech_with_retry(translated_text)
            
            logger.info(f"Complete: {len(audio_bytes)} bytes")
            
            return TranslationResult(
                success=True,
                audio_bytes=audio_bytes,
                original_text=original_text,
                translated_text=translated_text,
                detected_language=detected_language,
                target_language=target_lang_name
            )
        
        except OpenAIError as e:
            logger.error(f"OpenAI error: {str(e)}", exc_info=True)
            return TranslationResult(
                success=False,
                error_message=f"Service error: {str(e)}"
            )
        
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return TranslationResult(
                success=False,
                error_message="Unexpected error. Please try again."
            )
