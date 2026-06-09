from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from letterforge.models import ALL_CHARS
from letterforge.packaging import assemble_zip


def _make_output_files(chars=None) -> dict[str, bytes]:
    if chars is None:
        chars = ALL_CHARS
    return {c.filename: b"\x89PNG\r\n\x1a\n" + b"\x00" * 10 for c in chars}


def test_zip_contains_all_chars(tmp_path: Path):
    output_files = _make_output_files()
    output_zip = tmp_path / "out.zip"
    result_zip, results = assemble_zip(output_files, output_zip)

    assert result_zip.exists()
    with zipfile.ZipFile(result_zip) as zf:
        names = zf.namelist()

    for c in ALL_CHARS:
        assert c.filename in names


def test_zip_contains_manifest(tmp_path: Path):
    output_files = _make_output_files()
    output_zip = tmp_path / "out.zip"
    result_zip, _ = assemble_zip(output_files, output_zip)

    with zipfile.ZipFile(result_zip) as zf:
        assert "manifest.txt" in zf.namelist()
        manifest = zf.read("manifest.txt").decode()
    assert "missing" in manifest


def test_extraction_results_all_success(tmp_path: Path):
    output_files = _make_output_files()
    output_zip = tmp_path / "out.zip"
    _, results = assemble_zip(output_files, output_zip)

    assert all(r.success for r in results)
    assert len(results) == len(ALL_CHARS)


def test_missing_chars_reported(tmp_path: Path):
    # Only provide half the chars
    partial = ALL_CHARS[:10]
    output_files = _make_output_files(partial)
    output_zip = tmp_path / "out.zip"
    _, results = assemble_zip(output_files, output_zip)

    failures = [r for r in results if not r.success]
    assert len(failures) == len(ALL_CHARS) - 10


def test_manifest_reports_missing(tmp_path: Path):
    partial = ALL_CHARS[:5]
    output_files = _make_output_files(partial)
    output_zip = tmp_path / "out.zip"
    assemble_zip(output_files, output_zip)

    with zipfile.ZipFile(output_zip) as zf:
        manifest = zf.read("manifest.txt").decode()

    assert "missing (63)" in manifest


def test_unexpected_files_in_manifest(tmp_path: Path):
    output_files = _make_output_files()
    output_files["mystery_glyph.png"] = b"\x89PNG"
    output_zip = tmp_path / "out.zip"
    assemble_zip(output_files, output_zip)

    with zipfile.ZipFile(output_zip) as zf:
        manifest = zf.read("manifest.txt").decode()

    assert "mystery_glyph.png" in manifest
