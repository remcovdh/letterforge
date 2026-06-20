# letterforge

AI-powered typeface character sheet generator. Give it a reference image (your moodboard) and a
style prompt — it generates styled character sheets and extracts each of the 68 characters as an
individual transparent PNG, delivered as a ZIP file.

---

## Pipeline

```
reference image + style prompt
        │
        ▼  Step 1 — Image generation (gpt-image-2 / Google Imagen)
  3 character sheets
  • Sheet 1: A–Z uppercase    (9 cols × 3 rows, white background, magenta gutters)
  • Sheet 2: a–z lowercase    (9 cols × 3 rows, extra vertical padding for ascenders/descenders)
  • Sheet 3: 0–9 + ! ? . , ; : (5 cols × 4 rows, 4 empty trailing cells)
        │
        ▼  Step 2 — Code generation (Claude / GPT-4o / Gemini / Ollama)
  Python extraction script (LLM sees all 3 sheets; syntax-checked, up to 3 retry attempts)
        │
        ▼  Step 3 — Docker sandbox execution
  68 individual transparent PNGs (width-flexible — I is narrow, W is wide)
        │
        ▼  Step 4 — Deterministic post-processing
  Background + magenta bleed removed; tight crop + 4 px transparent padding
        │
        ▼  Step 5 — Packaging
  output.zip
```

---

## Quick start — Docker (recommended)

No local Python environment needed. Requires Docker with the Compose plugin.

```bash
git clone https://github.com/remcovdh/letterforge.git
cd letterforge

# fill in your API keys (OPENAI_API_KEY and ANTHROPIC_API_KEY required for the defaults)
cp .env.example .env
$EDITOR .env

# build the app image (one-time, ~30 s)
docker compose build

# generate a typeface — set WORK_DIR to the folder containing your moodboard
WORK_DIR=/path/to/your/images docker compose run --rm letterforge \
  generate moodboard.jpg "art nouveau with organic curved serifs"
```

Output lands in `$WORK_DIR/letterforge_output/`. The sandbox image
(`letterforge-sandbox:latest`) is built automatically on the first run via the Docker socket.

> **API keys:** the default pipeline uses `gpt-image-2` (OpenAI) for image generation and Claude
> for code generation, so both `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` must be set in `.env`.

---

## Quick start — local install

```bash
pip install letterforge[all]
cp .env.example .env           # fill in API keys
letterforge build-sandbox      # build the Docker sandbox image (one-time)
letterforge check-models       # health-check configured endpoints
letterforge generate moodboard.jpg "art nouveau with organic curved serifs"
```

---

## Installation

Install only what you need:

```bash
pip install letterforge[dalle]    # gpt-image-2 image model
pip install letterforge[imagen]   # Google Imagen image model
pip install letterforge[claude]   # Claude LLM
pip install letterforge[gpt4o]    # GPT-4o LLM
pip install letterforge[gemini]   # Gemini LLM
pip install letterforge[ollama]   # Ollama (local) LLM
pip install letterforge[all]      # everything
```

---

## Configuration

letterforge reads config from (highest precedence first):

1. Environment variables (`LETTERFORGE_*`)
2. `--config` flag pointing to a TOML or YAML file
3. Auto-discovered `letterforge.toml` / `letterforge.yaml` in the working directory
4. Built-in defaults

```toml
# letterforge.toml
image_model = "dalle"   # dalle | imagen
llm         = "claude"  # claude | gpt4o | gemini | ollama

[dalle]
model   = "gpt-image-2"
size    = "1536x1024"
quality = "high"

[claude]
model      = "claude-sonnet-4-6"
max_tokens = 4096

[sandbox]
timeout_seconds  = 60
network_disabled = true
```

---

## Python API

```python
from pathlib import Path
from letterforge import Pipeline, load_config

cfg = load_config()
pipeline = Pipeline(cfg)
result = pipeline.run(
    reference_image=Path("moodboard.jpg"),
    style_prompt="art nouveau with organic curved serifs",
    output_zip=Path("my_typeface.zip"),
)
print(f"ZIP: {result.output_zip}")
```

---

## CLI reference

```
letterforge generate REFERENCE_IMAGE STYLE_PROMPT [OPTIONS]

  Options:
    -o, --output PATH        Output ZIP path
    --image-model [dalle|imagen]
    --llm [claude|gpt4o|gemini|ollama]
    -c, --config PATH        Config file (TOML or YAML)

letterforge check-models     Health-check configured endpoints
letterforge build-sandbox    Build the Docker sandbox image
```

---

## Output format

```
characters/               ← 68 transparent PNGs, one per glyph
  upper_A.png … upper_Z.png
  lower_a.png … lower_z.png
  digit_0.png … digit_9.png
  punct_exclamation.png   (!)
  punct_question.png      (?)
  punct_period.png        (.)
  punct_comma.png         (,)
  punct_semicolon.png     (;)
  punct_colon.png         (:)
sheets/
  sheet1.png              ← A–Z uppercase
  sheet2.png              ← a–z lowercase
  sheet3.png              ← digits + punctuation
intermediate/
  extraction_code.py      ← the LLM-generated extraction script
manifest.txt              ← counts of found / missing / unexpected files
```

---

## Known limitations and edge cases

### White, black, or magenta in the glyph style

The segmentation algorithm relies on a hard contract:

| Element | Expected colour |
|---------|----------------|
| Sheet background | Pure white (#ffffff) or pure black (#000000) |
| Gutters between cells | Bright magenta (#FF00FF) |
| Glyphs | Anything *other* than the background colour or magenta |

If your moodboard features:

- **Dominant white or near-white tones** — the image model may render glyphs with white or very
  light ink. The background-removal step will then punch holes through those glyph pixels,
  because it cannot distinguish "white background" from "white ink stroke".
- **Dominant black or very dark tones** — same issue in reverse when the sheet uses a black
  background (currently only the digits+punctuation sheet).
- **Strong magenta or hot-pink tones** — the image model may bleed those hues into glyph strokes.
  The magenta-removal pass treats all `R>160, G<80, B>160` pixels as gutter bleed and makes them
  transparent, so magenta glyphs will develop holes.

**Practical advice:** choose moodboards where the dominant palette is in the mid-tones and warm or
cool colours — the algorithm is most reliable for dark-on-white and light-on-dark glyphs whose
hue stays well away from pure white, pure black, and magenta/pink.

### AI image generation variance

The image model (gpt-image-2) does not always respect the exact gutter-colour or grid-layout
requirements. Occasional issues:

- Gutter colour drifts toward a near-magenta pink, which still works but triggers slightly more
  aggressive removal than intended.
- Anti-aliasing along glyph edges extends fractionally into the gutter, which can join neighbouring
  characters in the detected cell span.
- Empty trailing cells in Sheet 3 may be filled with decorative elements.

The LLM-generated extraction code is the second variable layer — it sees the actual sheet images
and adapts, but it produces different code on every run. A syntax-check + retry loop (up to
3 attempts) catches the most common failure mode.

### Docker-in-Docker architecture

The sandbox container runs on the **host** Docker daemon (socket-mounted at
`/var/run/docker.sock`), not nested inside the app container. The host must have Docker available
and the socket must be accessible from the app container.

---

## Development history

A summary of the major design decisions made during iterative development:

| Commit | Change |
|--------|--------|
| `d5fbfd7` | Initial implementation: 2 sheets, arithmetic cell division, DALL-E 3 |
| `b2894f6` | Docker deployment support; gpt-image-2 compatibility (removed `response_format`) |
| `9ab9e71`–`eea581a` | Fixed API key propagation into Docker containers (SDK `api_key=None` bug) |
| `2bb6076` | LLM now receives labeled sheet images (SHEET 1 / SHEET 2); fixed off-by-one in cell extraction |
| `e9bdfff` | Switched cell detection to magenta projection-histogram gutter finding |
| `7eb4df7` | Split into 3 sheets; magenta gutters; width-flexible per-glyph PNGs |
| `2a294aa` | Intermediate results (sheets + extraction code) included in output ZIP |
| `4904dec` | SyntaxError in generated code now caught and fed back into retry loop |
| `2329a75` | Deterministic post-processing pass added (background removal, tight crop) |
| `c570a37` | numpy moved to main app dependencies (was sandbox-only) |
| `832f945` | Fixed white-background removal: PIL RGBA→RGB conversion was blackening transparent pixels, defeating majority-color detection |

**Key lessons:**

- `gpt-image-2` does not accept `response_format` or `size` values valid for DALL-E 3 — the
  parameter set changed significantly.
- OpenAI and Anthropic SDKs in recent versions do **not** fall back to environment variable API
  keys when `api_key=None` is passed explicitly — the kwarg must be omitted entirely.
- PIL's `Image.convert("RGB")` composites transparent RGBA pixels onto **black**, not white.
  When the sandbox code had already made white-background pixels transparent, corner-based
  background detection incorrectly identified the image as black-background. Fix: open as RGBA,
  extract RGB channels directly (`Image.fromarray(arr[:,:,:3])`), and detect background via
  majority-pixel counting across the whole image rather than just corners.
- Outer image margins look the same colour as cell backgrounds, so a naive "all runs of the
  non-foreground colour are gutters" approach includes the outer margins as extra cell boundaries
  (off-by-one). Fix: clip to the content bounding box first, then find only the inter-cell gutters.

---

## Backlog

- SVG vector output per character
- Font file assembly (.ttf / .otf)
- MCP server wrapper
- Detect and warn when moodboard palette overlaps background/gutter colours

---

## License

MIT
