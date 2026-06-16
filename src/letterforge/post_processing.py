from __future__ import annotations

import io
import logging

import numpy as np
from PIL import Image, ImageDraw

log = logging.getLogger(__name__)

# Sentinel colour used during flood-fill — must not appear naturally in any glyph
_SENTINEL = (253, 2, 253)
_FLOOD_TOLERANCE = 30   # max per-channel distance from corner pixel to count as background
_STRICT_WHITE = 228     # R,G,B all above this → definitely background on white sheet
_STRICT_BLACK = 27      # R,G,B all below this → definitely background on black sheet
_OUTPUT_PADDING = 4     # transparent px added on every side after tight crop


def clean_character_png(raw_bytes: bytes) -> bytes:
    """
    Deterministic post-processing applied to every character PNG that comes
    out of the sandbox, regardless of how well the LLM-generated code did:

    1. Detect background colour via majority-pixel counting (not corner sampling),
       so JPEG-compressed or partially-transparent images are handled correctly.
    2. Flood-fill from all four corners to mark connected background regions.
    3. Hard-threshold any near-background pixels not reached by the flood-fill.
    4. Remove any magenta (#FF00FF) gutter bleed.
    5. Tight-crop to the visible glyph, then add consistent 4 px padding.

    Falls back to the original bytes on any error so a processing bug
    never loses a character entirely.
    """
    try:
        return _clean(raw_bytes)
    except Exception as exc:
        log.warning("post_processing: skipped due to error: %s", exc)
        return raw_bytes


def _clean(raw_bytes: bytes) -> bytes:
    # Open as RGBA so we get the original RGB values without PIL compositing
    # transparency onto black (which is what .convert("RGB") does and breaks
    # white-background detection when the sandbox already made bg transparent).
    img_rgba = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
    w, h = img_rgba.size
    if w == 0 or h == 0:
        return raw_bytes

    arr = np.array(img_rgba, dtype=np.uint8)
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)

    # ── 1. Detect background via majority-pixel counting ──────────────────
    # Count near-white and near-black pixels across the whole image, excluding
    # magenta (gutter bleed).  Whichever count is larger is the background.
    is_magenta = (r > 160) & (g < 80) & (b > 160)
    near_white = ((r > 180) & (g > 180) & (b > 180) & ~is_magenta).sum()
    near_black = ((r < 75) & (g < 75) & (b < 75) & ~is_magenta).sum()
    is_white_bg = int(near_white) >= int(near_black)
    log.debug(
        "post_processing: near_white=%d near_black=%d → %s background",
        near_white, near_black, "white" if is_white_bg else "black",
    )

    # ── 2. Flood-fill from all four corners ───────────────────────────────
    # Build an RGB image directly from the original colour channels (no alpha
    # compositing) so that corners reflect the actual background colour even
    # when the sandbox already made background pixels transparent.
    img_rgb = Image.fromarray(arr[:, :, :3], "RGB")
    flood = img_rgb.copy()
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
    if is_white_bg:
        is_threshold_bg = (r > _STRICT_WHITE) & (g > _STRICT_WHITE) & (b > _STRICT_WHITE)
    else:
        is_threshold_bg = (r < _STRICT_BLACK) & (g < _STRICT_BLACK) & (b < _STRICT_BLACK)

    # ── 4. Build RGBA output ──────────────────────────────────────────────
    transparent = is_flood_bg | is_threshold_bg | is_magenta
    result = np.zeros((h, w, 4), dtype=np.uint8)
    result[:, :, :3] = arr[:, :, :3]
    result[:, :, 3] = np.where(transparent, 0, 255)

    # ── 5. Tight crop ─────────────────────────────────────────────────────
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

    # ── 6. Add consistent padding ─────────────────────────────────────────
    p = _OUTPUT_PADDING
    ph, pw = cropped.shape[0] + 2 * p, cropped.shape[1] + 2 * p
    padded = np.zeros((ph, pw, 4), dtype=np.uint8)
    padded[p:p + cropped.shape[0], p:p + cropped.shape[1]] = cropped

    out = Image.fromarray(padded, "RGBA")
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()
