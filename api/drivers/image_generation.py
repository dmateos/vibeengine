from typing import Any, Dict
import logging
import os
import base64
import requests

from .base import BaseDriver, DriverResponse

logger = logging.getLogger(__name__)


class ImageGenerationDriver(BaseDriver):
    type = "image_generation"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        node_id = node.get("id", "unknown")
        data = node.get("data") or {}
        label = data.get("label", "Image Generation")

        logger.info(f"[Image Generation] Node: {label} ({node_id})")

        # Get configuration
        provider = data.get("provider", "dalle").lower()
        model = data.get("model", "")
        api_key = data.get("api_key", "").strip()
        size = data.get("size", "1024x1024")
        quality = data.get("quality", "standard")
        style = data.get("style", "vivid")
        n_images = data.get("n_images", 1)

        # Get prompt
        prompt_template = data.get("prompt", "").strip()
        input_val = context.get("input", "")

        # If prompt template is empty, use input as prompt
        if not prompt_template:
            prompt = str(input_val)
        else:
            # Allow {input} placeholder in prompt template
            prompt = prompt_template.replace("{input}", str(input_val))

        if not prompt:
            return DriverResponse({
                "status": "error",
                "error": "No prompt provided for image generation",
            })

        logger.info(f"[Image Generation] Provider: {provider}, Prompt: {prompt[:100]}...")

        try:
            if provider == "dalle":
                return self._dalle_generation(prompt, model, api_key, size, quality, style, n_images)
            elif provider == "stability":
                return self._stability_generation(prompt, model, api_key, size)
            else:
                return DriverResponse({
                    "status": "error",
                    "error": f"Unsupported image generation provider: {provider}",
                })
        except Exception as e:
            logger.error(f"[Image Generation] Error: {str(e)}")
            return DriverResponse({
                "status": "error",
                "error": f"Image generation failed: {str(e)}",
            })

    def _dalle_generation(
        self,
        prompt: str,
        model: str,
        api_key: str,
        size: str,
        quality: str,
        style: str,
        n: int
    ) -> DriverResponse:
        """Generate images using DALL-E (OpenAI)."""
        try:
            import openai
        except ImportError:
            return DriverResponse({
                "status": "error",
                "error": "OpenAI library not installed. Run: pip install openai",
            })

        # Use API key from config or environment
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            return DriverResponse({
                "status": "error",
                "error": "OpenAI API key not provided",
            })

        # Default model
        if not model:
            model = "dall-e-3"

        client = openai.OpenAI(api_key=api_key)

        # DALL-E 3 only supports 1 image and specific sizes
        if model == "dall-e-3":
            n = 1
            if size not in ["1024x1024", "1792x1024", "1024x1792"]:
                size = "1024x1024"
        else:  # dall-e-2
            if size not in ["256x256", "512x512", "1024x1024"]:
                size = "1024x1024"
            quality = None  # DALL-E 2 doesn't support quality
            style = None  # DALL-E 2 doesn't support style

        # Build request params
        params = {
            "prompt": prompt,
            "model": model,
            "size": size,
            "n": int(n),
        }

        # Add DALL-E 3 specific params
        if model == "dall-e-3":
            if quality:
                params["quality"] = quality
            if style:
                params["style"] = style

        logger.info(f"[Image Generation] Calling DALL-E with model: {model}")
        response = client.images.generate(**params)

        # Extract image URLs
        images = []
        for img in response.data:
            images.append({
                "url": img.url,
                "revised_prompt": getattr(img, "revised_prompt", None),  # DALL-E 3 only
            })

        return DriverResponse({
            "status": "ok",
            "output": {
                "images": images,
                "prompt": prompt,
                "model": model,
                "provider": "dalle",
                "size": size,
                "quality": quality if model == "dall-e-3" else None,
                "style": style if model == "dall-e-3" else None,
            },
            "image_url": images[0]["url"] if images else None,  # For preview
        })

    def _stability_generation(
        self,
        prompt: str,
        model: str,
        api_key: str,
        size: str
    ) -> DriverResponse:
        """Generate images using Stability AI."""

        # Use API key from config or environment
        if not api_key:
            api_key = os.getenv("STABILITY_API_KEY")

        if not api_key:
            return DriverResponse({
                "status": "error",
                "error": "Stability AI API key not provided",
            })

        # Default model
        if not model:
            model = "stable-diffusion-xl-1024-v1-0"

        # Parse size
        try:
            width, height = map(int, size.split("x"))
        except:
            width, height = 1024, 1024

        # Stability AI API endpoint
        url = f"https://api.stability.ai/v1/generation/{model}/text-to-image"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "height": height,
            "width": width,
            "samples": 1,
            "steps": 30,
        }

        logger.info(f"[Image Generation] Calling Stability AI with model: {model}")
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            error_detail = response.json().get("message", "Unknown error")
            return DriverResponse({
                "status": "error",
                "error": f"Stability AI error: {error_detail}",
            })

        data = response.json()

        # Extract base64 images
        images = []
        for artifact in data.get("artifacts", []):
            if artifact.get("finishReason") == "SUCCESS":
                # Stability returns base64 encoded images
                base64_image = artifact.get("base64")
                images.append({
                    "base64": base64_image,
                    "seed": artifact.get("seed"),
                })

        if not images:
            return DriverResponse({
                "status": "error",
                "error": "No images generated by Stability AI",
            })

        return DriverResponse({
            "status": "ok",
            "output": {
                "images": images,
                "prompt": prompt,
                "model": model,
                "provider": "stability",
                "size": size,
            },
            "image_base64": images[0]["base64"] if images else None,  # For preview
        })
