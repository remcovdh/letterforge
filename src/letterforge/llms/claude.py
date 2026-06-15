from __future__ import annotations

from letterforge.config import ClaudeConfig, ConfigurationError
from letterforge.llms import register
from letterforge.llms.base import CodeGenRequest, CodeGenResponse, LLMAdapter
from letterforge.prompts import extract_code_block, reference_as_base64


@register("claude")
class ClaudeAdapter(LLMAdapter):
    def __init__(self, config: ClaudeConfig) -> None:
        try:
            import anthropic
        except ImportError:
            raise ConfigurationError(
                "anthropic package not installed. Run: pip install letterforge[claude]"
            )
        api_key = config.api_key.get_secret_value() if config.api_key else None
        self._client = anthropic.Anthropic(**({} if api_key is None else {"api_key": api_key}))
        self._config = config

    def generate_code(self, request: CodeGenRequest) -> CodeGenResponse:
        def img_block(path):
            data, media_type = reference_as_base64(path)
            return {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": data},
            }

        content: list[dict] = []
        for i, path in enumerate(request.sheet_image_paths, 1):
            content.append({"type": "text", "text": f"SHEET {i}:"})
            content.append(img_block(path))
        content.append({"type": "text", "text": request.user_prompt})

        message = self._client.messages.create(
            model=self._config.model,
            max_tokens=self._config.max_tokens,
            system=request.system_prompt,
            messages=[{"role": "user", "content": content}],
        )
        raw = message.content[0].text
        return CodeGenResponse(
            code=extract_code_block(raw),
            raw_response=raw,
            model_used=self._config.model,
        )

    def health_check(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False
