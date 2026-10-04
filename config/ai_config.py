"""
AI configuration — reads from environment variables with sensible defaults.
Set DEEPSEEK_API_KEY in your .env file or environment to override the default.
"""

import os

# DeepSeek API configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")

# AI model configuration
DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "2000"))
TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.7"))

# AI service configuration
AI_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "30"))
RETRY_COUNT = int(os.getenv("DEEPSEEK_RETRY_COUNT", "3"))
RETRY_DELAY = float(os.getenv("DEEPSEEK_RETRY_DELAY", "1"))
