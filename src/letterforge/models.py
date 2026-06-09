from __future__ import annotations

import math
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, model_validator


class CharCategory(str, Enum):
    UPPER = "upper"
    LOWER = "lower"
    DIGIT = "digit"
    PUNCT = "punct"


class Character(BaseModel):
    category: CharCategory
    char: str
    slug: str

    @property
    def filename(self) -> str:
        return f"{self.category.value}_{self.slug}.png"


def _upper(c: str) -> Character:
    return Character(category=CharCategory.UPPER, char=c, slug=c)


def _lower(c: str) -> Character:
    return Character(category=CharCategory.LOWER, char=c, slug=c)


def _digit(c: str) -> Character:
    return Character(category=CharCategory.DIGIT, char=c, slug=c)


_PUNCT_MAP = {
    "!": "exclamation",
    "?": "question",
    ".": "period",
    ",": "comma",
    ":": "colon",
    ";": "semicolon",
}


def _punct(c: str) -> Character:
    return Character(category=CharCategory.PUNCT, char=c, slug=_PUNCT_MAP[c])


SHEET1_CHARS: list[Character] = [
    *[_upper(c) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"],
    *[_digit(c) for c in "0123456789"],
    *[_punct(c) for c in "!?.,;:"],
]

SHEET2_CHARS: list[Character] = [
    *[_lower(c) for c in "abcdefghijklmnopqrstuvwxyz"],
]

ALL_CHARS: list[Character] = SHEET1_CHARS + SHEET2_CHARS

GRID_COLS = 9


class SheetSpec(BaseModel):
    sheet_index: int
    characters: list[Character]
    grid_cols: int = GRID_COLS
    grid_rows: int = 0

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def compute_rows(self) -> "SheetSpec":
        self.grid_rows = math.ceil(len(self.characters) / self.grid_cols)
        return self


class GeneratedSheet(BaseModel):
    spec: SheetSpec
    image_path: Path
    raw_bytes: bytes

    model_config = {"arbitrary_types_allowed": True}


class ExtractionResult(BaseModel):
    character: Character
    png_path: Path
    success: bool
    error: str | None = None

    model_config = {"arbitrary_types_allowed": True}


class PipelineResult(BaseModel):
    output_zip: Path
    sheets: list[GeneratedSheet]
    characters: list[ExtractionResult]
    generated_code: str
    sandbox_stdout: str
    sandbox_stderr: str

    model_config = {"arbitrary_types_allowed": True}


SHEET1_SPEC = SheetSpec(sheet_index=1, characters=SHEET1_CHARS)
SHEET2_SPEC = SheetSpec(sheet_index=2, characters=SHEET2_CHARS)
