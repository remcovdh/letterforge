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


# Sheet 1: uppercase only — 26 chars, 9 cols × 3 rows = 27 cells (1 empty)
UPPER_CHARS: list[Character] = [_upper(c) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]

# Sheet 2: lowercase only — 26 chars, 9 cols × 3 rows = 27 cells (1 empty)
# Gets extra vertical padding for ascenders/descenders
LOWER_CHARS: list[Character] = [_lower(c) for c in "abcdefghijklmnopqrstuvwxyz"]

# Sheet 3: digits + punctuation — 16 chars, 5 cols × 4 rows = 20 cells (4 empty)
# Wider cells give more room for naturally narrow (!) vs wide (0) glyphs
MISC_CHARS: list[Character] = [
    *[_digit(c) for c in "0123456789"],
    *[_punct(c) for c in "!?.,;:"],
]

ALL_CHARS: list[Character] = UPPER_CHARS + LOWER_CHARS + MISC_CHARS


class SheetSpec(BaseModel):
    sheet_index: int
    characters: list[Character]
    grid_cols: int
    grid_rows: int = 0
    # Bright magenta gutter: unambiguously detectable, distinct from white/black background
    gutter_color: str = "#FF00FF"
    # Extra vertical padding for sheets with ascenders/descenders (lowercase)
    extra_cell_padding: bool = False

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


SHEET1_SPEC = SheetSpec(sheet_index=1, characters=UPPER_CHARS, grid_cols=9)
SHEET2_SPEC = SheetSpec(sheet_index=2, characters=LOWER_CHARS, grid_cols=9, extra_cell_padding=True)
SHEET3_SPEC = SheetSpec(sheet_index=3, characters=MISC_CHARS, grid_cols=5)
