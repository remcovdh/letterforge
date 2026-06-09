from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CodeGenRequest:
    sheet1_image_path: Path
    sheet2_image_path: Path
    system_prompt: str
    user_prompt: str


@dataclass
class CodeGenResponse:
    code: str
    raw_response: str
    model_used: str


class LLMAdapter(ABC):
    @abstractmethod
    def generate_code(self, request: CodeGenRequest) -> CodeGenResponse: ...

    @abstractmethod
    def health_check(self) -> bool: ...
