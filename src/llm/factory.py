"""
LLM 工厂类
根据配置创建对应的 LLM Provider
"""

from typing import Optional, Dict, Any

from loguru import logger

from .base import LLMProvider
from .providers import OpenAIProvider, QwenProvider, GLMProvider, OllamaProvider


class LLMFactory:
    """LLM Provider 工厂"""
    
    _providers: Dict[str, type] = {
        "openai": OpenAIProvider,
        "qwen": QwenProvider,
        "glm": GLMProvider,
        "ollama": OllamaProvider,
    }
    
    _instances: Dict[str, LLMProvider] = {}
    
    @classmethod
    def register(cls, name: str, provider_class: type):
        """注册新的 Provider"""
        cls._providers[name] = provider_class
        logger.info(f"Registered LLM provider: {name}")
    
    @classmethod
    def create(
        cls,
        provider: str,
        **kwargs
    ) -> LLMProvider:
        """创建 Provider 实例"""
        if provider not in cls._providers:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(cls._providers.keys())}")
        
        provider_class = cls._providers[provider]
        return provider_class(**kwargs)
    
    @classmethod
    def get_or_create(
        cls,
        provider: str,
        **kwargs
    ) -> LLMProvider:
        """获取或创建 Provider 实例（单例模式）"""
        cache_key = f"{provider}:{kwargs.get('model', 'default')}"
        
        if cache_key not in cls._instances:
            cls._instances[cache_key] = cls.create(provider, **kwargs)
        
        return cls._instances[cache_key]
    
    @classmethod
    def clear_cache(cls):
        """清除缓存的实例"""
        cls._instances.clear()
    
    @classmethod
    def list_providers(cls) -> list:
        """列出所有可用的 providers"""
        return list(cls._providers.keys())


# 便捷函数
def get_llm(
    provider: Optional[str] = None,
    **kwargs
) -> LLMProvider:
    """获取 LLM 实例的便捷函数"""
    from src.config import get_settings
    
    settings = get_settings()
    
    if provider is None:
        provider = settings.llm.default_provider
    
    # 从配置获取 provider 设置
    provider_config = {}
    if hasattr(settings.llm, 'providers') and settings.llm.providers:
        provider_config = settings.llm.providers.get(provider, {})
        if hasattr(provider_config, 'dict'):
            provider_config = provider_config.dict()
        elif hasattr(provider_config, 'model_dump'):
            provider_config = provider_config.model_dump()
    
    # 合并配置
    config = {**provider_config, **kwargs}
    
    return LLMFactory.get_or_create(provider, **config)