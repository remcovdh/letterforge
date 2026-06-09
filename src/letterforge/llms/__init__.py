from __future__ import annotations

from typing import TYPE_CHECKING

from letterforge.llms.base import LLMAdapter

if TYPE_CHECKING:
    from letterforge.config import LetterforgeConfig

_REGISTRY: dict[str, type[LLMAdapter]] = {}


def register(name: str):
    def decorator(cls: type[LLMAdapter]) -> type[LLMAdapter]:
        _REGISTRY[name] = cls
        return cls

    return decorator


def get_llm(config: "LetterforgeConfig") -> LLMAdapter:
    from letterforge.llms import claude, gemini, gpt4o, ollama  # noqa: F401

    name = config.llm
    if name not in _REGISTRY:
        raise ValueError(f"Unknown LLM '{name}'. Available: {list(_REGISTRY)}")
    sub_config = getattr(config, name)
    return _REGISTRY[name](sub_config)


__all__ = ["LLMAdapter", "register", "get_llm"]
