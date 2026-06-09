from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from letterforge.config import LetterforgeConfig, load_config


@click.group()
@click.option(
    "--config",
    "-c",
    "config_file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Config file (letterforge.toml or letterforge.yaml)",
)
@click.option(
    "--image-model",
    type=click.Choice(["dalle", "imagen", "comfyui"]),
    default=None,
    help="Override image model",
)
@click.option(
    "--llm",
    type=click.Choice(["claude", "gpt4o", "gemini", "ollama"]),
    default=None,
    help="Override LLM for code generation",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx: click.Context, config_file, image_model, llm, verbose):
    """letterforge — AI-powered typeface character sheet generator."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
    else:
        logging.basicConfig(level=logging.INFO, stream=sys.stderr)

    cfg = load_config(config_file)
    if image_model:
        cfg = cfg.model_copy(update={"image_model": image_model})
    if llm:
        cfg = cfg.model_copy(update={"llm": llm})

    ctx.ensure_object(dict)
    ctx.obj["config"] = cfg


@cli.command("generate")
@click.argument("reference_image", type=click.Path(exists=True, path_type=Path))
@click.argument("style_prompt")
@click.option(
    "--output",
    "-o",
    "output_zip",
    type=click.Path(path_type=Path),
    default=None,
    help="Output ZIP path (default: <reference>_typeface.zip in output_dir)",
)
@click.pass_context
def generate(ctx: click.Context, reference_image: Path, style_prompt: str, output_zip):
    """
    Generate a typeface character set from a reference image.

    \b
    REFERENCE_IMAGE   Path to moodboard/style reference (PNG or JPEG)
    STYLE_PROMPT      Text description of the desired typeface style
    """
    from letterforge.pipeline import Pipeline

    cfg: LetterforgeConfig = ctx.obj["config"]
    pipeline = Pipeline(cfg)

    try:
        result = pipeline.run(
            reference_image=reference_image,
            style_prompt=style_prompt,
            output_zip=output_zip,
        )
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    success = sum(1 for r in result.characters if r.success)
    total = len(result.characters)
    click.echo(f"Done.")
    click.echo(f"Output ZIP: {result.output_zip}")
    click.echo(f"Characters extracted: {success}/{total}")
    if success < total:
        missing = [r.character.filename for r in result.characters if not r.success]
        click.echo(f"Missing: {', '.join(missing)}", err=True)


@cli.command("check-models")
@click.pass_context
def check_models(ctx: click.Context):
    """Health-check the configured image model and LLM endpoints."""
    from letterforge.image_models import get_image_model
    from letterforge.llms import get_llm

    cfg: LetterforgeConfig = ctx.obj["config"]

    try:
        img = get_image_model(cfg)
        ok = img.health_check()
        status = "OK" if ok else "UNREACHABLE"
        click.echo(f"Image model [{cfg.image_model}]: {status}")
    except Exception as exc:
        click.echo(f"Image model [{cfg.image_model}]: ERROR — {exc}", err=True)

    try:
        llm = get_llm(cfg)
        ok = llm.health_check()
        status = "OK" if ok else "UNREACHABLE"
        click.echo(f"LLM [{cfg.llm}]: {status}")
    except Exception as exc:
        click.echo(f"LLM [{cfg.llm}]: ERROR — {exc}", err=True)


@cli.command("build-sandbox")
@click.pass_context
def build_sandbox(ctx: click.Context):
    """Build the Docker sandbox image used for running extraction code."""
    from letterforge.sandbox.executor import DockerSandbox

    cfg: LetterforgeConfig = ctx.obj["config"]
    sandbox = DockerSandbox(cfg.sandbox)
    click.echo(f"Building sandbox image '{cfg.sandbox.docker_image}'...")
    try:
        sandbox.ensure_image()
        click.echo("Sandbox image ready.")
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
