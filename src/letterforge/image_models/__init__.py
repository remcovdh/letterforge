from __future__ import annotations

from typing import TYPE_CHECKING

from letterforge.image_models.base import ImageModelAdapter

if TYPE_CHECKING:
    from letterforge.config import LetterforgeConfig

_REGISTRY: dict[str, type[ImageModelAdapter]] = {}


def register(name: str):
    def decorator(cls: type[ImageModelAdapter]) -> type[ImageModelAdapter]:
        _REGISTRY[name] = cls
        return cls

    return decorator


def get_image_model(config: "LetterforgeConfig") -> ImageModelAdapter:
    # ensure all adapters are registered
    from letterforge.image_models import comfyui, dalle, imagen  # noqa: F401

    name = config.image_model
    if name not in _REGISTRY:
        raise ValueError(f"Unknown image model '{name}'. Available: {list(_REGISTRY)}")
    sub_config = getattr(config, name)
    return _REGISTRY[name](sub_config)


__all__ = ["ImageModelAdapter", "register", "get_image_model"]
