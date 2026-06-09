from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ImageGenerationRequest:
    prompt: str
    reference_image_path: Path
    width: int = 1792
    height: int = 1024
    sheet_index: int = 1
    reference_description: str = ""


@dataclass
class ImageGenerationResponse:
    image_bytes: bytes
    model_used: str
    revised_prompt: str | None = None


class ImageModelAdapter(ABC):
    @abstractmethod
    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse: ...

    @abstractmethod
    def health_check(self) -> bool: ...
