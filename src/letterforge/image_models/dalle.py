from __future__ import annotations

import base64

from letterforge.config import ConfigurationError, DalleConfig
from letterforge.image_models import register
from letterforge.image_models.base import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageModelAdapter,
)


@register("dalle")
class DalleAdapter(ImageModelAdapter):
    def __init__(self, config: DalleConfig) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ConfigurationError(
                "openai package not installed. Run: pip install letterforge[dalle]"
            )
        api_key = config.api_key.get_secret_value() if config.api_key else None
        self._client = OpenAI(**({} if api_key is None else {"api_key": api_key}))
        self._config = config

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        prompt = request.prompt
        if request.reference_description:
            prompt = f"Style reference: {request.reference_description}\n\n{prompt}"

        response = self._client.images.generate(
            model=self._config.model,
            prompt=prompt,
            size=self._config.size,  # type: ignore[arg-type]
            quality=self._config.quality,
            response_format="b64_json",
            n=1,
        )
        item = response.data[0]
        if item.b64_json:
            image_bytes = base64.b64decode(item.b64_json)
        elif item.url:
            import httpx
            image_bytes = httpx.get(item.url).content
        else:
            raise RuntimeError("No image data in API response")
        return ImageGenerationResponse(
            image_bytes=image_bytes,
            model_used=self._config.model,
            revised_prompt=item.revised_prompt,
        )

    def health_check(self) -> bool:
        try:
            self._client.models.retrieve(self._config.model)
            return True
        except Exception:
            return False
