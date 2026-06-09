from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def sample_png_bytes() -> bytes:
    """A minimal valid 10x10 white PNG image."""
    img = Image.new("RGB", (10, 10), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_reference_image(tmp_path: Path, sample_png_bytes: bytes) -> Path:
    p = tmp_path / "reference.png"
    p.write_bytes(sample_png_bytes)
    return p


@pytest.fixture
def sample_sheet_image(tmp_path: Path, sample_png_bytes: bytes) -> Path:
    p = tmp_path / "sheet.png"
    p.write_bytes(sample_png_bytes)
    return p
