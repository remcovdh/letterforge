from __future__ import annotations

import base64

from letterforge.config import ConfigurationError, ImagenConfig
from letterforge.image_models import register
from letterforge.image_models.base import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageModelAdapter,
)


@register("imagen")
class ImagenAdapter(ImageModelAdapter):
    def __init__(self, config: ImagenConfig) -> None:
        try:
            from google.cloud import aiplatform  # noqa: F401
        except ImportError:
            raise ConfigurationError(
                "google-cloud-aiplatform not installed. "
                "Run: pip install letterforge[imagen]"
            )
        self._config = config

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        from google.cloud import aiplatform
        from vertexai.preview.vision_models import ImageGenerationModel, Image

        aiplatform.init(
            project=self._config.project_id,
            location=self._config.location,
        )
        model = ImageGenerationModel.from_pretrained(self._config.model)

        # Pass reference image as style guidance
        ref_image = Image.load_from_file(str(request.reference_image_path))

        response = model.generate_images(
            prompt=request.prompt,
            number_of_images=1,
            aspect_ratio=self._config.aspect_ratio,
            reference_images=[ref_image],
        )
        image_bytes = response.images[0]._image_bytes
        return ImageGenerationResponse(
            image_bytes=image_bytes,
            model_used=self._config.model,
        )

    def health_check(self) -> bool:
        try:
            from google.cloud import aiplatform

            aiplatform.init(
                project=self._config.project_id,
                location=self._config.location,
            )
            return True
        except Exception:
            return False
