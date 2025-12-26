"""
Direct LLM API client without LangChain dependencies
"""
import json
from typing import Dict, List, Optional
from src.config import (
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    DEEPSEEK_API_KEY,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_PROVIDER,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    DEEPSEEK_API_BASE_URL,
)


class LLMClient:
    """Direct LLM API client supporting OpenAI, Anthropic, and DeepSeek"""
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ):
        """
        Initialize LLM client
        
        Args:
            provider: LLM provider ("openai", "anthropic", "deepseek")
            model: Model name
            temperature: Temperature setting
        """
        self.provider = provider or LLM_PROVIDER
        self.model = model or LLM_MODEL
        self.temperature = temperature if temperature is not None else LLM_TEMPERATURE
        
        # Initialize client based on provider
        if self.provider.lower() == "openai":
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=OPENAI_API_KEY)
            except ImportError:
                raise ImportError("openai package not installed. Install with: pip install openai")
        
        elif self.provider.lower() == "deepseek":
            if not DEEPSEEK_API_KEY:
                raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=DEEPSEEK_API_KEY,
                    base_url=DEEPSEEK_API_BASE_URL
                )
            except ImportError:
                raise ImportError("openai package not installed. Install with: pip install openai")
        
        elif self.provider.lower() == "anthropic":
            if not ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
            except ImportError:
                raise ImportError("anthropic package not installed. Install with: pip install anthropic")
        
        elif self.provider.lower() == "azure":
            if not all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME]):
                raise ValueError("Azure OpenAI configuration incomplete")
            try:
                from openai import AzureOpenAI
                self.client = AzureOpenAI(
                    api_key=AZURE_OPENAI_API_KEY,
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    api_version="2024-02-15-preview"
                )
                self.model = AZURE_OPENAI_DEPLOYMENT_NAME
            except ImportError:
                raise ImportError("openai package not installed. Install with: pip install openai")
        
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def call(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Call LLM API with messages
        
        Args:
            messages: List of message dicts with "role" and "content"
            max_tokens: Maximum tokens in response
            response_format: Optional response format (e.g., {"type": "json_object"})
            
        Returns:
            Response text from LLM
        """
        if self.provider.lower() in ["openai", "azure", "deepseek"]:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format
            
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        
        elif self.provider.lower() == "anthropic":
            # Anthropic API format
            system_message = None
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)
            
            kwargs = {
                "model": self.model,
                "messages": user_messages,
                "temperature": self.temperature,
                "max_tokens": max_tokens,
            }
            
            if system_message:
                kwargs["system"] = system_message
            
            response = self.client.messages.create(**kwargs)
            return response.content[0].text
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def extract_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict:
        """
        Call LLM and parse JSON response
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            Parsed JSON dictionary
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Request JSON format for OpenAI-compatible APIs
        response_format = None
        if self.provider.lower() in ["openai", "azure", "deepseek"]:
            response_format = {"type": "json_object"}
            # Add instruction to return JSON in prompt
            if "json" not in prompt.lower():
                prompt += "\n\nPlease return your response as a valid JSON object."
        
        response_text = self.call(messages, max_tokens=4000, response_format=response_format)
        
        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Try to extract JSON from text
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            raise ValueError(f"Failed to parse JSON response: {e}\nResponse: {response_text[:500]}")
