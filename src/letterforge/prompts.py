from __future__ import annotations

import base64
import re
from pathlib import Path

from letterforge.models import SheetSpec


SHEET_GENERATION_SYSTEM = "You are an expert type designer and illustrator."

CODE_GEN_SYSTEM = """\
You are an expert Python programmer specializing in image processing with PIL and OpenCV.
Your task is to write precise, robust Python code that segments a character sheet image
into individual character PNG files with transparent backgrounds.

Rules:
- Output ONLY a single Python code block, fenced with ```python ... ```.
- No explanations before or after the code block.
- The code must be fully self-contained and runnable with no user interaction.
- Use only: PIL (Pillow), cv2 (opencv-python-headless), numpy, pathlib, os.
- Input paths and output directory are provided via environment variables.
- Each output file must have a transparent background (RGBA mode).
"""


def build_sheet_prompt(spec: SheetSpec, user_style_prompt: str) -> str:
    char_list = "  ".join(c.char for c in spec.characters)
    n = len(spec.characters)

    return f"""\
Create a TYPEFACE CHARACTER SHEET — a clean grid of {n} styled glyphs arranged in \
{spec.grid_cols} columns × {spec.grid_rows} rows.

STYLE: {user_style_prompt}
Faithfully reproduce the aesthetic, materials, texture, and mood of the reference image \
as a consistent typographic style applied to every character.

LAYOUT REQUIREMENTS (critical — extraction code depends on this):
- Grid: exactly {spec.grid_cols} columns × {spec.grid_rows} rows
- Each cell is equal size with a clear, uniform margin between cells
- Pure white or solid black background (whichever maximises contrast with glyphs)
- Glyphs are centered within their cell
- No drop shadows bleeding into adjacent cells
- No decorative borders around the whole sheet
- No labels, captions, or any text other than the glyphs themselves

CHARACTERS IN READING ORDER (left-to-right, top-to-bottom):
{char_list}

Each character must be clearly legible and stylistically consistent with all others.
"""


def build_code_gen_prompt(spec1: SheetSpec, spec2: SheetSpec) -> str:
    def char_table(spec: SheetSpec) -> str:
        rows = []
        for i, c in enumerate(spec.characters):
            row, col = divmod(i, spec.grid_cols)
            rows.append(f"  row={row} col={col}  char={c.char!r}  output={c.filename}")
        return "\n".join(rows)

    return f"""\
You are given two character sheet images. Each is a uniform grid with {spec1.grid_cols} columns.

ENVIRONMENT VARIABLES available at runtime:
  SHEET1_PATH  — absolute path to sheet 1 image
  SHEET2_PATH  — absolute path to sheet 2 image
  OUTPUT_DIR   — directory where output PNGs must be written (already exists)

SHEET 1 character map ({len(spec1.characters)} characters, \
{spec1.grid_cols} cols × {spec1.grid_rows} rows):
{char_table(spec1)}

SHEET 2 character map ({len(spec2.characters)} characters, \
{spec2.grid_cols} cols × {spec2.grid_rows} rows):
{char_table(spec2)}

Implementation guidance:
1. For each sheet, detect the grid bounding box by cropping away outer margins \
   (find the first/last rows and columns containing non-background pixels).
2. Divide the bounding box into equal cells using the known column count and row count.
3. For each cell, extract the character region.
4. Convert to RGBA. Make the background colour transparent:
   - If background is white: use alpha thresholding on the luminance channel.
   - If background is black: invert the image first, then threshold.
   - Use flood-fill from all four corners to robustly detect background.
5. Trim transparent padding so each PNG is tightly cropped around the glyph, \
   with a small margin (4 px).
6. Save to OUTPUT_DIR with the exact filename from the character map above.

Process sheet 1 first, then sheet 2. Write the complete Python script now.
"""


def extract_code_block(raw: str) -> str:
    m = re.search(r"```python\s*(.*?)```", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Fallback: strip any markdown fences and return full text
    cleaned = re.sub(r"```\w*", "", raw).strip()
    return cleaned


def reference_as_base64_data_url(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    mime = "image/png" if suffix == "png" else "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def reference_as_base64(path: Path) -> tuple[str, str]:
    """Returns (base64_data, media_type) for use in API image blocks."""
    suffix = path.suffix.lower().lstrip(".")
    media_type = "image/png" if suffix == "png" else "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode()
    return data, media_type
