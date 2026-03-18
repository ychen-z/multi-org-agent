"""
LLM 工厂类
根据配置创建对应的 LLM Provider
"""

from typing import Optional, Dict, Any

from Logging import logger

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
    """
    获取 LLM 实例的便捷函数
    
    支持从环境变量自动配置:
    - DEFAULT_LLM_PROVIDER: 默认 provider (openai/qwen/glm/ollama)
    - OPENAI_API_KEY: OpenAI API Key
    - BASE_URL: 自定义 base URL (用于 OpenAI 兼容接口如 MiniMax)
    """
    from src.config import get_settings
    
    settings = get_settings()
    
    # 优先使用环境变量中的 default_llm_provider
    if provider is None:
        env_provider = settings.default_llm_provider
        # 如果是 OpenAI 兼容的第三方 provider，映射到 openai
        if env_provider and env_provider.lower() not in ["openai", "qwen", "glm", "ollama"]:
            provider = "openai"  # 使用 OpenAI provider 但配合自定义 base_url
        else:
            provider = env_provider or settings.llm.default_provider
    
    # 从配置获取 provider 设置
    provider_config = {}
    if hasattr(settings.llm, 'providers') and settings.llm.providers:
        provider_config = settings.llm.providers.get(provider, {})
        if hasattr(provider_config, 'dict'):
            provider_config = provider_config.dict()
        elif hasattr(provider_config, 'model_dump'):
            provider_config = provider_config.model_dump()
    
    # 从环境变量补充配置
    if provider == "openai":
        if not provider_config.get("api_key") and settings.openai_api_key:
            provider_config["api_key"] = settings.openai_api_key
        if not provider_config.get("base_url") and settings.base_url:
            provider_config["base_url"] = settings.base_url
        # MiniMax 等兼容 provider 可能需要特定 model
        if settings.default_llm_provider and settings.default_llm_provider.lower() not in ["openai"]:
            if not provider_config.get("model"):
                provider_config["model"] = settings.default_llm_provider
    elif provider == "qwen":
        if not provider_config.get("api_key") and settings.qwen_api_key:
            provider_config["api_key"] = settings.qwen_api_key
    elif provider == "glm":
        if not provider_config.get("api_key") and settings.glm_api_key:
            provider_config["api_key"] = settings.glm_api_key
    elif provider == "ollama":
        if not provider_config.get("base_url") and settings.ollama_base_url:
            provider_config["base_url"] = settings.ollama_base_url
    
    # 合并配置
    config = {**provider_config, **kwargs}
    
    logger.debug(f"Creating LLM: provider={provider}, config keys={list(config.keys())}")
    
    return LLMFactory.get_or_create(provider, **config)
