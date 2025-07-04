"""
Configuration management for Web Inference
"""
import os
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseSettings, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # LLM Configuration
    llm_provider: Literal["openai", "anthropic", "local"] = "openai"
    llm_model: str = "gpt-4-turbo-preview"
    llm_endpoint: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Browser Configuration
    browser: Literal["chromium", "firefox", "webkit"] = "chromium"
    headless: bool = False
    browser_timeout: int = 30000  # milliseconds
    
    # Storage
    database_url: str = "sqlite:///data/web_inference.db"
    data_dir: Path = Path("data")
    
    # Analysis Configuration
    min_element_size: int = 50  # Minimum size for analyzable elements
    max_elements_per_page: int = 100  # Limit to prevent overload
    confidence_threshold: float = 0.7  # Minimum confidence for high rating
    
    # Visual Overlay
    overlay_opacity: float = 0.3
    show_confidence_colors: bool = True
    enable_click_explanations: bool = True
    
    # Web Interface
    flask_port: int = 5000
    flask_debug: bool = False
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @validator("openai_api_key", "anthropic_api_key")
    def validate_api_keys(cls, v, values):
        """Ensure appropriate API key is set based on provider"""
        provider = values.get("llm_provider")
        if provider == "openai" and not values.get("openai_api_key") and not v:
            raise ValueError("OpenAI API key required when using OpenAI provider")
        if provider == "anthropic" and not values.get("anthropic_api_key") and not v:
            raise ValueError("Anthropic API key required when using Anthropic provider")
        return v
    
    @validator("data_dir")
    def create_data_dir(cls, v):
        """Ensure data directory exists"""
        v.mkdir(parents=True, exist_ok=True)
        (v / "site_knowledge").mkdir(exist_ok=True)
        (v / "patterns").mkdir(exist_ok=True)
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()

# Confidence level thresholds
CONFIDENCE_LEVELS = {
    "high": 0.8,
    "medium": 0.5,
    "low": 0.0
}

# Element selectors to ignore
IGNORED_SELECTORS = [
    "script",
    "style",
    "noscript",
    "iframe",
    "svg path",
    "br",
    "hr"
]

# Semantic section patterns
SECTION_PATTERNS = {
    "navigation": ["nav", "menu", "navbar", "navigation"],
    "header": ["header", "masthead", "banner"],
    "footer": ["footer", "bottom", "copyright"],
    "content": ["main", "content", "article", "section"],
    "sidebar": ["sidebar", "aside", "widget"],
    "search": ["search", "find", "query"],
    "login": ["login", "signin", "auth"],
    "contact": ["contact", "email", "phone", "address"]
}