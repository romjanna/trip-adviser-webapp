"""
Configuration management for translation service
"""
import os
from dataclasses import dataclass
from enum import Enum


class Environment(Enum):
    """Deployment environment"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class Config:
    """Application configuration"""
    
    # Environment
    ENV: Environment
    DEBUG: bool
    
    # API Keys
    OPENAI_API_KEY: str
    
    # Flask settings
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    
    # Translation settings
    MAX_FILE_SIZE_MB: int = 25
    MIN_CONFIDENCE_SCORE: float = 0.7
    MAX_RETRIES: int = 3
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # CORS settings
    CORS_ORIGINS: list = None
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables"""
        
        env_name = os.getenv('ENV', 'development')
        env = Environment(env_name)
        
        # Required environment variables
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        cors_origins = os.getenv('CORS_ORIGINS', '*')
        origins_list = cors_origins.split(',') if cors_origins else ['*']
        
        return cls(
            ENV=env,
            DEBUG=env == Environment.DEVELOPMENT,
            OPENAI_API_KEY=openai_api_key,
            HOST=os.getenv('HOST', '0.0.0.0'),
            PORT=int(os.getenv('PORT', '8080')),
            MAX_FILE_SIZE_MB=int(os.getenv('MAX_FILE_SIZE_MB', '25')),
            MIN_CONFIDENCE_SCORE=float(os.getenv('MIN_CONFIDENCE_SCORE', '0.7')),
            MAX_RETRIES=int(os.getenv('MAX_RETRIES', '3')),
            LOG_LEVEL=os.getenv('LOG_LEVEL', 'INFO'),
            CORS_ORIGINS=origins_list
        )
