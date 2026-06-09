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

## Quick start

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
pip install letterforge[dalle]    # DALL-E 3 image model
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

Each character is saved as `{category}_{slug}.png` with a transparent background:

| Example filename      | Character |
|-----------------------|-----------|
| `upper_A.png`         | A         |
| `lower_a.png`         | a         |
| `digit_0.png`         | 0         |
| `punct_exclamation.png` | !       |

The ZIP also contains a `manifest.txt` listing any missing or unexpected files.

## Backlog

- SVG vector output per character
- Font file assembly (.ttf / .otf)
- MCP server wrapper

## License

MIT
