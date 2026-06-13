from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(Exception):
    pass


class DalleConfig(BaseModel):
    api_key: SecretStr | None = None
    model: str = "gpt-image-2"
    size: str = "1536x1024"
    quality: Literal["low", "medium", "high", "auto"] = "high"


class ImagenConfig(BaseModel):
    project_id: str | None = None
    location: str = "us-central1"
    model: str = "imagegeneration@006"
    aspect_ratio: str = "16:9"


class ComfyUIConfig(BaseModel):
    base_url: str = "http://localhost:8188"
    workflow_template: Path | None = None
    timeout_seconds: int = 120


class ClaudeConfig(BaseModel):
    api_key: SecretStr | None = None
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 4096


class GPT4oConfig(BaseModel):
    api_key: SecretStr | None = None
    model: str = "gpt-4o"
    max_tokens: int = 4096


class GeminiConfig(BaseModel):
    api_key: SecretStr | None = None
    model: str = "gemini-1.5-pro"
    max_tokens: int = 4096


class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    model: str = "llama3"
    max_tokens: int = 4096


class SandboxConfig(BaseModel):
    docker_image: str = "letterforge-sandbox:latest"
    mem_limit: str = "512m"
    cpu_quota: int = 50000
    timeout_seconds: int = 60
    network_disabled: bool = True
    auto_build: bool = True


class LetterforgeConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LETTERFORGE_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    image_model: Literal["dalle", "imagen", "comfyui"] = "dalle"
    llm: Literal["claude", "gpt4o", "gemini", "ollama"] = "claude"
    output_dir: Path = Path("./letterforge_output")
    work_dir: Path = Path("/tmp/letterforge")

    dalle: DalleConfig = Field(default_factory=DalleConfig)
    imagen: ImagenConfig = Field(default_factory=ImagenConfig)
    comfyui: ComfyUIConfig = Field(default_factory=ComfyUIConfig)
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    gpt4o: GPT4oConfig = Field(default_factory=GPT4oConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)


def load_config(config_file: Path | None = None) -> LetterforgeConfig:
    overrides: dict[str, Any] = {}

    if config_file is None:
        for candidate in ["letterforge.toml", "letterforge.yaml", "letterforge.yml"]:
            p = Path(candidate)
            if p.exists():
                config_file = p
                break

    if config_file is not None:
        overrides = _parse_config_file(config_file)

    return LetterforgeConfig(**overrides)


def _parse_config_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".toml":
        with open(path, "rb") as f:
            return tomllib.load(f)
    if suffix in (".yaml", ".yml"):
        import yaml

        with open(path) as f:
            return yaml.safe_load(f) or {}
    raise ValueError(f"Unsupported config file format: {suffix}")
