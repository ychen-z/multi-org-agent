"""
配置管理模块
支持 YAML 配置文件和环境变量
"""

import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


def load_yaml_with_env(file_path: str) -> dict:
    """加载 YAML 文件并解析环境变量"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析 ${VAR:default} 格式的环境变量
    pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
    
    def replace_env(match):
        var_name = match.group(1)
        default_value = match.group(2) or ''
        return os.environ.get(var_name, default_value)
    
    content = re.sub(pattern, replace_env, content)
    return yaml.safe_load(content)


class MongoDBConfig(BaseModel):
    uri: str = "mongodb://localhost:27017"
    database: str = "hr_analytics"
    max_pool_size: int = 100
    min_pool_size: int = 10


class LLMProviderConfig(BaseModel):
    api_key: Optional[str] = None
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    base_url: Optional[str] = None


class LLMConfig(BaseModel):
    default_provider: str = "openai"
    providers: dict[str, LLMProviderConfig] = {}


class AgentConfig(BaseModel):
    orchestrator: dict = {}
    data_governance: dict = {}
    recruitment: dict = {}
    performance: dict = {}
    talent_risk: dict = {}
    org_health: dict = {}


class DataGenerationConfig(BaseModel):
    seed: int = 42
    default_employee_count: int = 5000000
    distributions: dict = {}


class APIConfig(BaseModel):
    prefix: str = "/api/v1"
    cors: dict = {}


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = ""
    file: dict = {}


class CacheConfig(BaseModel):
    enabled: bool = True
    ttl_seconds: int = 3600
    max_size: int = 1000


class AppConfig(BaseModel):
    name: str = "HR Analytics Multi-Agent System"
    version: str = "1.0.0"
    debug: bool = False


class Settings(BaseSettings):
    """全局配置类"""
    
    app: AppConfig = AppConfig()
    database: dict = {}
    llm: LLMConfig = LLMConfig()
    agents: AgentConfig = AgentConfig()
    data_generation: DataGenerationConfig = DataGenerationConfig()
    api: APIConfig = APIConfig()
    logging: LoggingConfig = LoggingConfig()
    cache: CacheConfig = CacheConfig()
    
    # 从环境变量读取的配置
    environment: str = "development"
    mongodb_uri: str = "mongodb://localhost:27017"
    openai_api_key: Optional[str] = None
    qwen_api_key: Optional[str] = None
    glm_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    default_llm_provider: str = "openai"
    base_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外的环境变量


# 全局配置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局配置实例"""
    global _settings
    
    if _settings is None:
        # 查找配置文件
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        
        if config_path.exists():
            config_data = load_yaml_with_env(str(config_path))
            _settings = Settings(**config_data)
        else:
            _settings = Settings()
    
    return _settings


def reload_settings() -> Settings:
    """重新加载配置"""
    global _settings
    _settings = None
    return get_settings()


# 便捷访问
settings = get_settings()
