from __future__ import annotations

from letterforge.config import ConfigurationError, GeminiConfig
from letterforge.llms import register
from letterforge.llms.base import CodeGenRequest, CodeGenResponse, LLMAdapter
from letterforge.prompts import extract_code_block


@register("gemini")
class GeminiAdapter(LLMAdapter):
    def __init__(self, config: GeminiConfig) -> None:
        try:
            import google.generativeai as genai
        except ImportError:
            raise ConfigurationError(
                "google-generativeai not installed. Run: pip install letterforge[gemini]"
            )
        api_key = config.api_key.get_secret_value() if config.api_key else None
        if api_key:
            genai.configure(api_key=api_key)
        self._genai = genai
        self._config = config

    def generate_code(self, request: CodeGenRequest) -> CodeGenResponse:
        import PIL.Image

        model = self._genai.GenerativeModel(
            model_name=self._config.model,
            system_instruction=request.system_prompt,
        )

        sheet1 = PIL.Image.open(request.sheet1_image_path)
        sheet2 = PIL.Image.open(request.sheet2_image_path)

        response = model.generate_content(
            [sheet1, sheet2, request.user_prompt],
            generation_config=self._genai.GenerationConfig(
                max_output_tokens=self._config.max_tokens,
            ),
        )
        raw = response.text
        return CodeGenResponse(
            code=extract_code_block(raw),
            raw_response=raw,
            model_used=self._config.model,
        )

    def health_check(self) -> bool:
        try:
            list(self._genai.list_models())
            return True
        except Exception:
            return False
