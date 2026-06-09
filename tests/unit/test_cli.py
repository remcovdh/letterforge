from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from letterforge.cli.main import cli
from letterforge.models import ALL_CHARS, ExtractionResult, PipelineResult


@pytest.fixture
def runner():
    return CliRunner()


def _make_pipeline_result(tmp_path: Path) -> PipelineResult:
    zip_path = tmp_path / "out.zip"
    zip_path.write_bytes(b"PK")
    return PipelineResult(
        output_zip=zip_path,
        sheets=[],
        characters=[
            ExtractionResult(
                character=c,
                png_path=zip_path.parent / c.filename,
                success=True,
            )
            for c in ALL_CHARS
        ],
        generated_code="print('done')",
        sandbox_stdout="",
        sandbox_stderr="",
    )


def test_generate_command_success(runner, tmp_path, sample_reference_image):
    mock_result = _make_pipeline_result(tmp_path)

    with patch("letterforge.pipeline.Pipeline") as MockPipeline:
        instance = MockPipeline.return_value
        instance.run.return_value = mock_result

        result = runner.invoke(
            cli,
            ["generate", str(sample_reference_image), "art nouveau"],
        )

    assert result.exit_code == 0
    assert "Done" in result.output
    assert "68/68" in result.output


def test_generate_command_missing_reference(runner, tmp_path):
    result = runner.invoke(
        cli,
        ["generate", str(tmp_path / "nonexistent.png"), "art nouveau"],
    )
    assert result.exit_code != 0


def test_check_models_command(runner):
    with (
        patch("letterforge.image_models.get_image_model") as mock_img,
        patch("letterforge.llms.get_llm") as mock_llm,
    ):
        mock_img.return_value.health_check.return_value = True
        mock_llm.return_value.health_check.return_value = True

        result = runner.invoke(cli, ["check-models"])

    assert result.exit_code == 0
    assert "OK" in result.output


def test_check_models_unreachable(runner):
    with (
        patch("letterforge.image_models.get_image_model") as mock_img,
        patch("letterforge.llms.get_llm") as mock_llm,
    ):
        mock_img.return_value.health_check.return_value = False
        mock_llm.return_value.health_check.return_value = False

        result = runner.invoke(cli, ["check-models"])

    assert result.exit_code == 0
    assert "UNREACHABLE" in result.output


def test_build_sandbox_command(runner):
    with patch("letterforge.sandbox.executor.DockerSandbox") as MockSandbox:
        MockSandbox.return_value.ensure_image.return_value = None
        result = runner.invoke(cli, ["build-sandbox"])

    assert result.exit_code == 0
    assert "ready" in result.output


def test_image_model_override(runner, tmp_path, sample_reference_image):
    mock_result = _make_pipeline_result(tmp_path)

    with patch("letterforge.pipeline.Pipeline") as MockPipeline:
        instance = MockPipeline.return_value
        instance.run.return_value = mock_result

        result = runner.invoke(
            cli,
            ["--image-model", "imagen", "generate", str(sample_reference_image), "test"],
        )

    called_cfg = MockPipeline.call_args[0][0]
    assert called_cfg.image_model == "imagen"
