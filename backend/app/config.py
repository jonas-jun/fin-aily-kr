from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    gemini_api_key: str = ""
    dart_api_key: str = ""
    app_env: str = "development"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

@lru_cache
def get_settings() -> Settings:
    return Settings()


@dataclass
class FeatureModelConfig:
    provider: str
    model: str


@lru_cache
def _load_model_config() -> dict:
    config_path = Path(__file__).parent / "model_config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_feature_config(feature: str) -> FeatureModelConfig:
    config = _load_model_config()
    feat = config.get("features", {}).get(feature, config.get("defaults", {}))
    return FeatureModelConfig(
        provider=feat["provider"],
        model=feat["model"],
    )
