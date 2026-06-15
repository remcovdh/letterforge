from __future__ import annotations

import logging
from pathlib import Path

from letterforge.config import LetterforgeConfig, load_config
from letterforge.image_models import get_image_model
from letterforge.image_models.base import ImageGenerationRequest
from letterforge.llms import get_llm
from letterforge.llms.base import CodeGenRequest
from letterforge.models import (
    SHEET1_SPEC,
    SHEET2_SPEC,
    SHEET3_SPEC,
    GeneratedSheet,
    PipelineResult,
    SheetSpec,
)
from letterforge.packaging import assemble_zip
from letterforge.prompts import (
    CODE_GEN_SYSTEM,
    SHEET_GENERATION_SYSTEM,
    build_code_gen_prompt,
    build_sheet_prompt,
)
from letterforge.sandbox.executor import DockerSandbox, SandboxTimeoutError
from letterforge.sandbox.validator import validate_generated_code

log = logging.getLogger(__name__)

_MAX_CODE_GEN_RETRIES = 3
_ALL_SPECS = [SHEET1_SPEC, SHEET2_SPEC, SHEET3_SPEC]


class Pipeline:
    def __init__(self, config: LetterforgeConfig | None = None) -> None:
        self.config = config or load_config()
        self.image_model = get_image_model(self.config)
        self.llm = get_llm(self.config)
        self.sandbox = DockerSandbox(self.config.sandbox)

    def run(
        self,
        reference_image: Path,
        style_prompt: str,
        output_zip: Path | None = None,
    ) -> PipelineResult:
        if not reference_image.exists():
            raise FileNotFoundError(f"Reference image not found: {reference_image}")

        output_zip = output_zip or (
            self.config.output_dir / f"{reference_image.stem}_typeface.zip"
        )
        output_zip.parent.mkdir(parents=True, exist_ok=True)

        work_dir = self.config.work_dir
        work_dir.mkdir(parents=True, exist_ok=True)

        log.info("Step 1: generating character sheets")
        sheets = self._generate_sheets(reference_image, style_prompt, work_dir)

        log.info("Step 2: generating extraction code via %s", self.config.llm)
        code = self._generate_extraction_code_with_retry(sheets)

        log.info("Step 3: running extraction code in Docker sandbox")
        sandbox_result = self.sandbox.run(
            code=code,
            sheet_bytes=[s.raw_bytes for s in sheets],
        )

        if sandbox_result.timed_out:
            raise SandboxTimeoutError(
                f"Sandbox timed out after {self.config.sandbox.timeout_seconds}s"
            )
        if sandbox_result.exit_code != 0:
            raise RuntimeError(
                f"Sandbox exited with code {sandbox_result.exit_code}:\n"
                f"{sandbox_result.stderr}"
            )

        log.info(
            "Step 4: packaging %d PNGs into %s",
            len(sandbox_result.output_files),
            output_zip,
        )
        result_zip, extraction_results = assemble_zip(
            output_files=sandbox_result.output_files,
            output_zip=output_zip,
            sheets=sheets,
            generated_code=code,
        )

        return PipelineResult(
            output_zip=result_zip,
            sheets=sheets,
            characters=extraction_results,
            generated_code=code,
            sandbox_stdout=sandbox_result.stdout,
            sandbox_stderr=sandbox_result.stderr,
        )

    def _generate_sheets(
        self,
        reference_image: Path,
        style_prompt: str,
        work_dir: Path,
    ) -> list[GeneratedSheet]:
        reference_description = ""
        if self.config.image_model == "dalle":
            reference_description = self._describe_reference_image(reference_image)

        sheets: list[GeneratedSheet] = []
        for spec in _ALL_SPECS:
            prompt = build_sheet_prompt(spec, style_prompt)
            req = ImageGenerationRequest(
                prompt=prompt,
                reference_image_path=reference_image,
                sheet_index=spec.sheet_index,
                reference_description=reference_description,
            )
            log.info("  generating sheet %d (%d chars)", spec.sheet_index, len(spec.characters))
            resp = self.image_model.generate(req)

            image_path = work_dir / f"sheet{spec.sheet_index}.png"
            image_path.write_bytes(resp.image_bytes)

            sheets.append(
                GeneratedSheet(spec=spec, image_path=image_path, raw_bytes=resp.image_bytes)
            )
        return sheets

    def _describe_reference_image(self, reference_image: Path) -> str:
        req = CodeGenRequest(
            sheet_image_paths=[reference_image],
            system_prompt=(
                "You are an expert art director. "
                "Describe the visual style of the provided image in 2-3 sentences, "
                "focusing on: colors, textures, materials, mood, and typographic character. "
                "Be concise and specific — this description will guide an AI image generator."
            ),
            user_prompt="Describe the visual style of this reference image.",
        )
        resp = self.llm.generate_code(req)
        return resp.raw_response.strip()

    def _generate_extraction_code_with_retry(self, sheets: list[GeneratedSheet]) -> str:
        user_prompt = build_code_gen_prompt([s.spec for s in sheets])
        violations_feedback = ""

        for attempt in range(1, _MAX_CODE_GEN_RETRIES + 1):
            prompt = user_prompt
            if violations_feedback:
                prompt = (
                    f"Your previous code had errors that must be fixed:\n"
                    f"{violations_feedback}\n\n"
                    f"Generate a corrected, complete Python script that fixes every issue above.\n\n"
                    f"{user_prompt}"
                )

            req = CodeGenRequest(
                sheet_image_paths=[s.image_path for s in sheets],
                system_prompt=CODE_GEN_SYSTEM,
                user_prompt=prompt,
            )
            resp = self.llm.generate_code(req)
            violations = validate_generated_code(resp.code)

            if not violations:
                return resp.code

            violations_feedback = "\n".join(f"- {v}" for v in violations)
            log.warning(
                "Code gen attempt %d/%d failed safety check: %s",
                attempt,
                _MAX_CODE_GEN_RETRIES,
                violations,
            )

        raise ValueError(
            f"Generated code failed safety validation after {_MAX_CODE_GEN_RETRIES} attempts. "
            f"Last violations: {violations_feedback}"
        )
