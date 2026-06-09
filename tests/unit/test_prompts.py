from __future__ import annotations

from pathlib import Path

import pytest

from letterforge.models import SHEET1_SPEC, SHEET2_SPEC
from letterforge.prompts import (
    build_code_gen_prompt,
    build_sheet_prompt,
    extract_code_block,
    reference_as_base64,
    reference_as_base64_data_url,
)


def test_sheet_prompt_contains_grid_dimensions():
    prompt = build_sheet_prompt(SHEET1_SPEC, "art nouveau")
    assert f"{SHEET1_SPEC.grid_cols} columns" in prompt
    assert f"{SHEET1_SPEC.grid_rows} rows" in prompt


def test_sheet_prompt_contains_all_chars():
    prompt = build_sheet_prompt(SHEET1_SPEC, "art nouveau")
    for c in SHEET1_SPEC.characters:
        assert c.char in prompt


def test_sheet_prompt_contains_style():
    prompt = build_sheet_prompt(SHEET1_SPEC, "futuristic neon")
    assert "futuristic neon" in prompt


def test_code_gen_prompt_contains_filenames():
    prompt = build_code_gen_prompt(SHEET1_SPEC, SHEET2_SPEC)
    assert "upper_A.png" in prompt
    assert "lower_a.png" in prompt
    assert "digit_0.png" in prompt
    assert "punct_exclamation.png" in prompt


def test_code_gen_prompt_contains_env_vars():
    prompt = build_code_gen_prompt(SHEET1_SPEC, SHEET2_SPEC)
    assert "SHEET1_PATH" in prompt
    assert "SHEET2_PATH" in prompt
    assert "OUTPUT_DIR" in prompt


def test_extract_code_block_fenced():
    raw = 'Here is the code:\n```python\nprint("hello")\n```\nDone.'
    code = extract_code_block(raw)
    assert code == 'print("hello")'


def test_extract_code_block_fallback():
    raw = 'print("hello")'
    code = extract_code_block(raw)
    assert "hello" in code


def test_extract_code_block_multiline():
    raw = "```python\nimport os\nprint(os.environ)\n```"
    code = extract_code_block(raw)
    assert "import os" in code
    assert "print" in code


def test_reference_as_base64(sample_reference_image: Path):
    data, media_type = reference_as_base64(sample_reference_image)
    assert media_type == "image/png"
    assert len(data) > 0
    import base64
    decoded = base64.b64decode(data)
    assert decoded[:4] == b"\x89PNG"


def test_reference_as_base64_data_url(sample_reference_image: Path):
    url = reference_as_base64_data_url(sample_reference_image)
    assert url.startswith("data:image/png;base64,")
