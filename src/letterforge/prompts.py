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

LAYOUT REQUIREMENTS (critical — automatic segmentation depends on strict compliance):
- Grid: exactly {spec.grid_cols} columns × {spec.grid_rows} rows
- Each cell is equal size
- GUTTERS: between every pair of adjacent columns, and between every pair of adjacent rows, \
there must be a solid-colour strip at least 24 pixels wide. The gutter colour must be \
identical to the sheet background — no ink, stroke, shadow, texture, or decoration \
of any kind may enter a gutter strip.
- Background: pure white (#ffffff) or pure black (#000000) — whichever maximises contrast \
with the glyphs. Every gutter and outer margin must be this same solid colour.
- Each glyph is centred within its cell with at least 10 px clear padding from each gutter edge
- No drop shadows, halos, or glow effects that bleed into gutters
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
You are given two character sheet images. Each is a grid with {spec1.grid_cols} columns \
and wide solid-colour gutter strips between every cell (at least 24 px wide, same colour \
as the sheet background).

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
1. Load the sheet in grayscale (keep a colour copy for cropping).
2. Detect background: sample a 10 px border around all four edges; \
   if the median sample value > 128 the background is white, otherwise black.
3. Build a binary foreground mask (numpy bool array, True = ink pixel):
   - White background: True where grayscale value < 200
   - Black background: True where grayscale value > 55
4. Clip to content bounding box: find the first and last row, and first and last \
   column, that contain at least one True pixel. All subsequent steps work \
   within this bounding box only. This excludes outer margins so they are \
   never mistaken for cell gutters.
5. Find COLUMN boundaries via vertical projection histogram (within bounding box):
   a. col_hist[x] = count of True pixels in bounding-box column x
   b. Gutter columns: col_hist[x] <= 2 (pure background, allowing 2 px JPEG noise)
   c. Identify runs of consecutive gutter columns → these are the gutter spans
   d. Cell column spans = the runs of non-gutter columns between those gutter spans \
      (the bounding box left and right edges are boundaries, NOT gutter spans)
   e. Verify exactly {spec1.grid_cols} column spans were found; \
      if not, divide the bounding box width into {spec1.grid_cols} equal spans instead
6. Find ROW boundaries the same way using a horizontal projection histogram, \
   expecting exactly {{row_count}} row spans per sheet.
7. For each cell (row_idx, col_idx) — row_idx and col_idx are 0-based:
   a. Map to the character at position (row_idx * grid_cols + col_idx) in the \
      character map; skip if the position is beyond the character count
   b. Crop the COLOUR image (not the grayscale) to the cell's column span × row span \
      within the bounding box
   c. Convert the crop to RGBA
   d. Flood-fill background to alpha=0 from all 4 corners using PIL ImageDraw.floodfill \
      with tolerance 30 on the RGB values; repeat on the grayscale-converted version \
      if flood-fill misses enclosed background areas
   e. Additionally set any pixel to alpha=0 where: \
      white bg → R>230 and G>230 and B>230; black bg → R<25 and G<25 and B<25
   f. Trim fully-transparent border rows/cols (where entire row/col alpha == 0), \
      then pad with 4 px of fully transparent pixels on all sides
   g. Save as PNG to OUTPUT_DIR with the exact filename from the character map
8. Process SHEET 1 first (using SHEET 1's grid_cols and row count), \
   then SHEET 2 (using SHEET 2's grid_cols and row count). \
   Write the complete, self-contained Python script now.
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
