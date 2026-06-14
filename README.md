# letterforge

AI-powered typeface character sheet generator. Give it a reference image (your moodboard) and a style prompt — it generates styled character sheets and extracts each letter as an individual transparent PNG, delivered as a ZIP file.

## Pipeline

```
reference image + style prompt
        │
        ▼  Step 1 — Image generation (DALL-E 3 / Google Imagen / ComfyUI)
  2 character sheets
  • Sheet 1: A-Z  0-9  ! ? . , : ;
  • Sheet 2: a-z
        │
        ▼  Step 2 — Code generation (Claude / GPT-4o / Gemini / Ollama)
  Python extraction script
        │
        ▼  Step 3 — Docker sandbox execution
  68 individual transparent PNGs
        │
        ▼  Step 4 — Packaging
  output.zip
```

## Quick start — Docker (recommended)

No local Python environment needed. Requires Docker with the Compose plugin.

```bash
git clone https://github.com/remcovdh/letterforge.git
cd letterforge

# fill in your API keys (OPENAI_API_KEY and ANTHROPIC_API_KEY are required for the defaults)
cp .env.example .env
$EDITOR .env

# build the app image (one-time, ~30 s)
docker compose build

# generate a typeface — set WORK_DIR to the folder containing your moodboard
WORK_DIR=/path/to/your/images docker compose run --rm letterforge \
  generate moodboard.jpg "art nouveau with organic curved serifs"
```

Output lands in `$WORK_DIR/letterforge_output/`. The sandbox image
(`letterforge-sandbox:latest`) is built automatically on the first run.

> **Note:** the default pipeline uses `gpt-image-2` (OpenAI) for image
> generation and Claude for the LLM, so both `OPENAI_API_KEY` and
> `ANTHROPIC_API_KEY` must be set in `.env`.

## Quick start — local install

```bash
pip install letterforge[all]

# copy and fill in your API keys
cp .env.example .env

# build the Docker sandbox image (one-time)
letterforge build-sandbox

# health-check your configured endpoints
letterforge check-models

# generate a typeface
letterforge generate moodboard.jpg "art nouveau with organic curved serifs"
```

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

## Configuration

letterforge reads config from (highest precedence first):

1. Environment variables (`LETTERFORGE_*`)
2. `--config` flag pointing to a TOML or YAML file
3. Auto-discovered `letterforge.toml` / `letterforge.yaml` in the working directory
4. Built-in defaults

```toml
# letterforge.toml
image_model = "dalle"   # dalle | imagen | comfyui
llm         = "claude"  # claude | gpt4o | gemini | ollama

[dalle]
model   = "dall-e-3"
size    = "1792x1024"
quality = "hd"

[claude]
model      = "claude-sonnet-4-6"
max_tokens = 4096

[sandbox]
timeout_seconds  = 60
network_disabled = true
```

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

## CLI reference

```
letterforge generate REFERENCE_IMAGE STYLE_PROMPT [OPTIONS]

  Options:
    -o, --output PATH        Output ZIP path
    --image-model [dalle|imagen|comfyui]
    --llm [claude|gpt4o|gemini|ollama]
    -c, --config PATH        Config file (TOML or YAML)

letterforge check-models     Health-check configured endpoints
letterforge build-sandbox    Build the Docker sandbox image
```

## Output format

The ZIP is organised into folders:

```
characters/          ← 68 transparent PNGs, one per glyph
  upper_A.png
  lower_a.png
  digit_0.png
  punct_exclamation.png
  ...
sheets/              ← the generated character-sheet images
  sheet1.png         (A–Z, 0–9, punctuation)
  sheet2.png         (a–z)
intermediate/
  extraction_code.py ← the LLM-generated extraction script
manifest.txt         ← counts of found / missing / unexpected files
```

| Example filename                   | Character |
|------------------------------------|-----------|
| `characters/upper_A.png`           | A         |
| `characters/lower_a.png`           | a         |
| `characters/digit_0.png`           | 0         |
| `characters/punct_exclamation.png` | !         |

## Backlog

- SVG vector output per character
- Font file assembly (.ttf / .otf)
- MCP server wrapper

## License

MIT
