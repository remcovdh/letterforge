from __future__ import annotations

from pathlib import Path

import pytest

from letterforge.config import LetterforgeConfig, load_config, _parse_config_file


def test_default_config():
    cfg = LetterforgeConfig()
    assert cfg.image_model == "dalle"
    assert cfg.llm == "claude"
    assert cfg.sandbox.timeout_seconds == 60
    assert cfg.sandbox.network_disabled is True


def test_load_config_toml(tmp_path: Path):
    toml = tmp_path / "letterforge.toml"
    toml.write_text('[project]\nimage_model = "imagen"\nllm = "gpt4o"\n')
    cfg = load_config(toml)
    # pydantic-settings reads top-level keys; no [project] nesting in our schema
    # so this file only has nested section — defaults apply
    assert cfg.image_model == "dalle"  # not overridden by nested section


def test_load_config_toml_flat(tmp_path: Path):
    toml = tmp_path / "letterforge.toml"
    toml.write_text('image_model = "imagen"\nllm = "gemini"\n')
    cfg = load_config(toml)
    assert cfg.image_model == "imagen"
    assert cfg.llm == "gemini"


def test_load_config_yaml(tmp_path: Path):
    yaml_file = tmp_path / "letterforge.yaml"
    yaml_file.write_text("image_model: comfyui\nllm: ollama\n")
    cfg = load_config(yaml_file)
    assert cfg.image_model == "comfyui"
    assert cfg.llm == "ollama"


def test_parse_config_file_unsupported(tmp_path: Path):
    f = tmp_path / "config.json"
    f.write_text("{}")
    with pytest.raises(ValueError, match="Unsupported"):
        _parse_config_file(f)


def test_sandbox_config_defaults():
    cfg = LetterforgeConfig()
    assert cfg.sandbox.docker_image == "letterforge-sandbox:latest"
    assert cfg.sandbox.mem_limit == "512m"
    assert cfg.sandbox.auto_build is True


def test_dalle_config_defaults():
    cfg = LetterforgeConfig()
    assert cfg.dalle.model == "dall-e-3"
    assert cfg.dalle.quality == "hd"


def test_claude_config_default_model():
    cfg = LetterforgeConfig()
    assert cfg.claude.model == "claude-sonnet-4-6"
