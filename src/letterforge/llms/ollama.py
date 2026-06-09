from __future__ import annotations

from letterforge.config import ConfigurationError, OllamaConfig
from letterforge.llms import register
from letterforge.llms.base import CodeGenRequest, CodeGenResponse, LLMAdapter
from letterforge.prompts import extract_code_block, reference_as_base64


@register("ollama")
class OllamaAdapter(LLMAdapter):
    def __init__(self, config: OllamaConfig) -> None:
        try:
            import ollama as ollama_lib
        except ImportError:
            raise ConfigurationError(
                "ollama package not installed. Run: pip install letterforge[ollama]"
            )
        self._ollama = ollama_lib
        self._config = config

    def generate_code(self, request: CodeGenRequest) -> CodeGenResponse:
        def img_data(path) -> str:
            data, _ = reference_as_base64(path)
            return data

        response = self._ollama.chat(
            model=self._config.model,
            messages=[
                {"role": "system", "content": request.system_prompt},
                {
                    "role": "user",
                    "content": request.user_prompt,
                    "images": [
                        img_data(request.sheet1_image_path),
                        img_data(request.sheet2_image_path),
                    ],
                },
            ],
            options={"num_predict": self._config.max_tokens},
        )
        raw = response["message"]["content"]
        return CodeGenResponse(
            code=extract_code_block(raw),
            raw_response=raw,
            model_used=self._config.model,
        )

    def health_check(self) -> bool:
        try:
            client = self._ollama.Client(host=self._config.base_url)
            client.list()
            return True
        except Exception:
            return False
