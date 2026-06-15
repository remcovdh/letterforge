from __future__ import annotations

import io
import logging

import numpy as np
from PIL import Image, ImageDraw

log = logging.getLogger(__name__)

# Sentinel colour used during flood-fill — must not appear naturally in any glyph
_SENTINEL = (253, 2, 253)
_FLOOD_TOLERANCE = 20   # max colour distance from corner pixel to count as background
_STRICT_WHITE = 242     # R,G,B all above this → definitely background on white sheet
_STRICT_BLACK = 13      # R,G,B all below this → definitely background on black sheet
_OUTPUT_PADDING = 4     # transparent px added on every side after tight crop


def clean_character_png(raw_bytes: bytes) -> bytes:
    """
    Deterministic post-processing applied to every character PNG that comes
    out of the sandbox, regardless of how well the LLM-generated code did:

    1. Remove any magenta (#FF00FF) gutter bleed.
    2. Flood-fill from all four corners with a tolerance to mark connected
       background regions as transparent (catches missed outer background).
    3. Hard-threshold any near-white / near-black pixels not reached by
       the flood-fill (catches patches isolated from corners by thin glyphs).
    4. Tight-crop to the visible glyph, then add consistent 4 px padding.

    Falls back to the original bytes on any error so a processing bug
    never loses a character entirely.
    """
    try:
        return _clean(raw_bytes)
    except Exception as exc:
        log.warning("post_processing: skipped due to error: %s", exc)
        return raw_bytes


def _clean(raw_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    w, h = img.size
    if w == 0 or h == 0:
        return raw_bytes

    arr = np.array(img, dtype=np.uint8)

    # ── 1. Detect background colour from corners ──────────────────────────
    corner_pixels = np.array([
        arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]
    ], dtype=float)
    avg_lum = corner_pixels.mean()
    is_white_bg = avg_lum > 128

    # ── 2. Flood-fill from all four corners ───────────────────────────────
    # PIL floodfill modifies the image in-place; we fill with our sentinel.
    flood = img.copy()
    for xy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        try:
            ImageDraw.floodfill(flood, xy, _SENTINEL, thresh=_FLOOD_TOLERANCE)
        except Exception:
            pass

    flood_arr = np.array(flood, dtype=np.uint8)
    is_flood_bg = (
        (flood_arr[:, :, 0] == _SENTINEL[0]) &
        (flood_arr[:, :, 1] == _SENTINEL[1]) &
        (flood_arr[:, :, 2] == _SENTINEL[2])
    )

    # ── 3. Hard-threshold near-background pixels ──────────────────────────
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    if is_white_bg:
        is_threshold_bg = (r > _STRICT_WHITE) & (g > _STRICT_WHITE) & (b > _STRICT_WHITE)
    else:
        is_threshold_bg = (r < _STRICT_BLACK) & (g < _STRICT_BLACK) & (b < _STRICT_BLACK)

    # ── 4. Remove magenta gutter bleed ───────────────────────────────────
    is_magenta = (r > 160) & (g < 80) & (b > 160)

    # ── 5. Build RGBA output ──────────────────────────────────────────────
    transparent = is_flood_bg | is_threshold_bg | is_magenta
    result = np.zeros((h, w, 4), dtype=np.uint8)
    result[:, :, :3] = arr
    result[:, :, 3] = np.where(transparent, 0, 255)

    # ── 6. Tight crop ─────────────────────────────────────────────────────
    alpha = result[:, :, 3]
    visible_rows = np.any(alpha > 0, axis=1)
    visible_cols = np.any(alpha > 0, axis=0)

    if not visible_rows.any():
        log.warning("post_processing: character is entirely transparent after cleanup")
        return raw_bytes  # don't return a blank PNG

    r0, r1 = int(np.where(visible_rows)[0][[0, -1]].tolist()[0]), \
              int(np.where(visible_rows)[0][[0, -1]].tolist()[1])
    c0, c1 = int(np.where(visible_cols)[0][[0, -1]].tolist()[0]), \
              int(np.where(visible_cols)[0][[0, -1]].tolist()[1])
    cropped = result[r0:r1 + 1, c0:c1 + 1]

    # ── 7. Add consistent padding ─────────────────────────────────────────
    p = _OUTPUT_PADDING
    ph, pw = cropped.shape[0] + 2 * p, cropped.shape[1] + 2 * p
    padded = np.zeros((ph, pw, 4), dtype=np.uint8)
    padded[p:p + cropped.shape[0], p:p + cropped.shape[1]] = cropped

    out = Image.fromarray(padded, "RGBA")
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()
