from __future__ import annotations

from letterforge.config import ConfigurationError, GPT4oConfig
from letterforge.llms import register
from letterforge.llms.base import CodeGenRequest, CodeGenResponse, LLMAdapter
from letterforge.prompts import extract_code_block, reference_as_base64_data_url


@register("gpt4o")
class GPT4oAdapter(LLMAdapter):
    def __init__(self, config: GPT4oConfig) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ConfigurationError(
                "openai package not installed. Run: pip install letterforge[gpt4o]"
            )
        api_key = config.api_key.get_secret_value() if config.api_key else None
        self._client = OpenAI(**({} if api_key is None else {"api_key": api_key}))
        self._config = config

    def generate_code(self, request: CodeGenRequest) -> CodeGenResponse:
        def img_url(path):
            return {
                "type": "image_url",
                "image_url": {"url": reference_as_base64_data_url(path), "detail": "high"},
            }

        response = self._client.chat.completions.create(
            model=self._config.model,
            max_tokens=self._config.max_tokens,
            messages=[
                {"role": "system", "content": request.system_prompt},
                {
                    "role": "user",
                    "content": [
                        item
                        for i, path in enumerate(request.sheet_image_paths, 1)
                        for item in (
                            {"type": "text", "text": f"SHEET {i}:"},
                            img_url(path),
                        )
                    ] + [{"type": "text", "text": request.user_prompt}],
                },
            ],
        )
        raw = response.choices[0].message.content or ""
        return CodeGenResponse(
            code=extract_code_block(raw),
            raw_response=raw,
            model_used=self._config.model,
        )

    def health_check(self) -> bool:
        try:
            self._client.models.retrieve(self._config.model)
            return True
        except Exception:
            return False
