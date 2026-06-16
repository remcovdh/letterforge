from __future__ import annotations

import base64
import re
from pathlib import Path

from letterforge.models import SheetSpec


SHEET_GENERATION_SYSTEM = "You are an expert type designer and illustrator."

CODE_GEN_SYSTEM = """\
You are an expert Python programmer specializing in image processing with PIL and OpenCV.
Your task is to write precise, robust Python code that segments character sheet images
into individual character PNG files with transparent backgrounds.

Rules:
- Output ONLY a single Python code block, fenced with ```python ... ```.
- No explanations before or after the code block.
- The code must be fully self-contained and runnable with no user interaction.
- Use only: PIL (Pillow), cv2 (opencv-python-headless), numpy, pathlib, os.
- Input paths and output directory are provided via environment variables.
- Each output PNG must be RGBA with the cell background fully transparent.
- Each output PNG must be tightly cropped to the visible glyph with 4 px transparent padding —
  no cell background area included, and the glyph width/height reflects its natural proportions.

Self-check your code before finishing:
- Verify that every variable is defined before use (no NameError at runtime).
- Verify that array indexing uses the correct axis order: arr[row, col] or arr[y, x].
- Verify that every opened image path comes from os.environ, not a hardcoded string.
- Verify that the output loop saves exactly the right filename for each (row, col) cell.
"""


def build_sheet_prompt(spec: SheetSpec, user_style_prompt: str) -> str:
    char_list = "  ".join(c.char for c in spec.characters)
    n = len(spec.characters)
    total_cells = spec.grid_cols * spec.grid_rows
    empty_cells = total_cells - n

    empty_note = (
        f"The last {empty_cells} cell(s) must be left empty (background colour only, no glyph)."
        if empty_cells > 0
        else ""
    )

    padding_note = (
        "LOWERCASE VERTICAL PADDING: these glyphs have ascenders and descenders. "
        "Each glyph must occupy only the central 60% of the cell height — "
        "leave at least 20% clear background above (for ascenders: h b d k l t) "
        "and 20% clear background below (for descenders: g j p q y). "
        "This space is required for correct automatic extraction."
        if spec.extra_cell_padding
        else "Each glyph is centred within its cell with balanced padding on all sides."
    )

    return f"""\
Create a TYPEFACE CHARACTER SHEET — a grid of {n} styled glyphs arranged in \
{spec.grid_cols} columns × {spec.grid_rows} rows ({total_cells} cells total).

STYLE: {user_style_prompt}
Faithfully reproduce the aesthetic, materials, texture, and mood of the reference image \
as a consistent typographic style applied to every character.

LAYOUT REQUIREMENTS (critical — automatic segmentation depends on strict compliance):
- Grid: exactly {spec.grid_cols} columns × {spec.grid_rows} rows
- Each cell is equal size
- {empty_note}
- GUTTERS: between every pair of adjacent columns and between every pair of adjacent rows \
there must be a solid strip at least 24 pixels wide coloured BRIGHT MAGENTA (#FF00FF). \
This is non-negotiable — the gutter colour MUST be #FF00FF with no blending, \
no anti-aliasing, and no other colour mixed in. \
No ink, stroke, shadow, or texture may enter any gutter strip.
- Cell background: pure white (#ffffff) or pure black (#000000), \
whichever maximises contrast with the glyphs. \
All outer margins use the same cell background colour (NOT magenta).
- {padding_note}
- No drop shadows or halos that bleed across gutter boundaries
- No decorative frame around the whole sheet
- No labels, captions, or text other than the glyph characters themselves

CHARACTERS IN READING ORDER (left-to-right, top-to-bottom):
{char_list}

Every character must be clearly legible and stylistically consistent across the whole sheet.
"""


def build_code_gen_prompt(specs: list[SheetSpec]) -> str:
    def char_table(spec: SheetSpec) -> str:
        rows = []
        for i, c in enumerate(spec.characters):
            row, col = divmod(i, spec.grid_cols)
            rows.append(f"  row={row} col={col}  →  {c.filename}")
        return "\n".join(rows)

    sheet_sections = "\n\n".join(
        f"SHEET {s.sheet_index} — {len(s.characters)} characters, "
        f"{s.grid_cols} cols × {s.grid_rows} rows "
        f"({s.grid_cols * s.grid_rows} cells, last {s.grid_cols * s.grid_rows - len(s.characters)} empty):\n"
        + char_table(s)
        for s in specs
    )

    env_vars = "\n".join(
        f"  SHEET{s.sheet_index}_PATH  — path to sheet {s.sheet_index} image"
        for s in specs
    )

    sheet_tuples = ", ".join(
        f"({s.sheet_index}, {s.grid_cols}, {s.grid_rows}, {len(s.characters)})"
        for s in specs
    )

    return f"""\
You are given {len(specs)} character sheet images (labeled SHEET 1 through SHEET {len(specs)} \
above each image). Each sheet has:
- A pure white or pure black cell background
- BRIGHT MAGENTA (#FF00FF) gutter strips between every cell (≥24 px wide)
- Outer margins that are the SAME colour as the cell background (NOT magenta)

ENVIRONMENT VARIABLES:
{env_vars}
  OUTPUT_DIR   — directory for output PNGs (already exists)

CHARACTER MAPS:
{sheet_sections}

ALGORITHM — implement all steps exactly as described:

Step 1 — GUTTER DETECTION (per sheet):
  Load the image as RGBA (keep a colour copy). Convert to numpy.
  Build a boolean magenta mask: pixel is magenta where R > 160 AND G < 80 AND B > 160.
  Column histogram: col_hist[x] = number of magenta pixels in column x.
  Row histogram: row_hist[y] = number of magenta pixels in row y.
  Find gutter spans: runs of consecutive columns where col_hist[x] >= 5 (at least 5 magenta px).
  Similarly find row gutter spans.
  Cell column spans = the runs of NON-gutter columns between the gutter spans.
    Important: the outer left/right margins are NOT gutter spans — only strips between cells are.
    To exclude outer margins: after finding gutter spans, treat the gaps between them as cell spans.
    If the number of cell column spans found does not equal the expected grid_cols,
    fall back to dividing the full image width into grid_cols equal spans.
  Cell row spans = same logic, must equal grid_rows.

Step 2 — CELL EXTRACTION (per cell):
  For cell at (row_idx, col_idx), crop the colour image to [row_span × col_span].
  (row_idx and col_idx are 0-based; character index = row_idx * grid_cols + col_idx.)
  Skip cells where character index >= character count (empty trailing cells).

Step 3 — BACKGROUND REMOVAL (per cell crop):
  Convert the crop to RGBA.
  Detect background colour using MAJORITY PIXEL COUNTING across the WHOLE crop
  (not just corners — corners may be occupied by a glyph that touches the edge):
    near_white = count pixels where R>180 AND G>180 AND B>180 AND NOT magenta
    near_black = count pixels where R<75  AND G<75  AND B<75  AND NOT magenta
    If near_white >= near_black → white background; else → black background.
  White background: set alpha=0 for all pixels where R>215 AND G>215 AND B>215.
  Black background: set alpha=0 for all pixels where R<40 AND G<40 AND B<40.
  Then flood-fill from each of the 4 corners of the crop using PIL ImageDraw.floodfill
  with thresh=30, replacing the background colour with a sentinel transparent colour.
  Convert any sentinel pixels to alpha=0.
  This two-pass approach (threshold + flood-fill) removes background both inside enclosed
  counters and around the outer glyph edges.

Step 4 — TIGHT CROP (per cell):
  Trim all fully-transparent border rows and columns (where every pixel has alpha=0).
  This makes naturally narrow glyphs (like "I" or "!") produce narrow PNGs, and wide
  glyphs (like "W" or "M") produce wide PNGs — proportional to the actual glyph.
  Add 4 px of fully-transparent padding on all four sides.
  Save as PNG to OUTPUT_DIR using the exact filename from the character map.

Process sheets in order: {sheet_tuples}.
Write the complete, self-contained, runnable Python script now.
"""


def extract_code_block(raw: str) -> str:
    m = re.search(r"```python\s*(.*?)```", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
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
