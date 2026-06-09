from __future__ import annotations

import base64
import json
import time
import uuid
from pathlib import Path

import httpx

from letterforge.config import ComfyUIConfig
from letterforge.image_models import register
from letterforge.image_models.base import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageModelAdapter,
)

_DEFAULT_WORKFLOW: dict = {
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "cfg": 7,
            "denoise": 1,
            "latent_image": ["5", 0],
            "model": ["4", 0],
            "negative": ["7", 0],
            "positive": ["6", 0],
            "sampler_name": "euler",
            "scheduler": "normal",
            "seed": 42,
            "steps": 20,
        },
    },
    "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5-pruned-emaonly.ckpt"}},
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {"batch_size": 1, "height": 1024, "width": 1792},
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["4", 1], "text": "PROMPT_PLACEHOLDER"},
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["4", 1], "text": "ugly, blurry, low quality"},
    },
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    "9": {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "letterforge_", "images": ["8", 0]},
    },
}


@register("comfyui")
class ComfyUIAdapter(ImageModelAdapter):
    def __init__(self, config: ComfyUIConfig) -> None:
        self._config = config
        self._client = httpx.Client(base_url=config.base_url, timeout=config.timeout_seconds)

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        workflow = self._load_workflow()

        # Inject prompt into the text encoder node
        for node in workflow.values():
            if node.get("class_type") == "CLIPTextEncode":
                if "PROMPT_PLACEHOLDER" in str(node["inputs"].get("text", "")):
                    node["inputs"]["text"] = request.prompt
                    break

        client_id = str(uuid.uuid4())
        resp = self._client.post(
            "/prompt",
            json={"prompt": workflow, "client_id": client_id},
        )
        resp.raise_for_status()
        prompt_id = resp.json()["prompt_id"]

        image_bytes = self._poll_result(prompt_id)
        return ImageGenerationResponse(
            image_bytes=image_bytes,
            model_used="comfyui",
        )

    def _poll_result(self, prompt_id: str) -> bytes:
        deadline = time.time() + self._config.timeout_seconds
        while time.time() < deadline:
            history = self._client.get(f"/history/{prompt_id}").json()
            if prompt_id in history:
                outputs = history[prompt_id]["outputs"]
                for node_output in outputs.values():
                    for img in node_output.get("images", []):
                        img_resp = self._client.get(
                            "/view",
                            params={
                                "filename": img["filename"],
                                "subfolder": img.get("subfolder", ""),
                                "type": img.get("type", "output"),
                            },
                        )
                        img_resp.raise_for_status()
                        return img_resp.content
            time.sleep(2)
        raise TimeoutError(f"ComfyUI timed out waiting for prompt {prompt_id}")

    def _load_workflow(self) -> dict:
        if self._config.workflow_template and self._config.workflow_template.exists():
            with open(self._config.workflow_template) as f:
                return json.load(f)
        import copy

        return copy.deepcopy(_DEFAULT_WORKFLOW)

    def health_check(self) -> bool:
        try:
            resp = self._client.get("/system_stats", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
