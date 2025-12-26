"""
Configuration file for LLM API settings
"""
import os

# Try to load .env or LLM_variables.env file if python-dotenv is installed
try:
    from dotenv import load_dotenv
    # Try to load LLM_variables.env first, then .env
    if os.path.exists('LLM_variables.env'):
        load_dotenv('LLM_variables.env')
    else:
        load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, will use system environment variables

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Model Configuration
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")  # "openai", "anthropic", "deepseek"

# DeepSeek API Configuration
DEEPSEEK_API_BASE_URL = os.getenv("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com")

# Azure OpenAI (optional)
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
