# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tool for generating images using Gemini API."""

import base64
import enum
import os
from typing import Any

from google import genai
from google.genai import interactions
from google.genai import types
import pydantic

from google.antigravity import types as sdk_types


class AspectRatio(str, enum.Enum):
  SQUARE = "1:1"
  WIDE = "16:9"
  TALL = "3:4"
  VERTICAL = "9:16"


class ImageSize(str, enum.Enum):
  SIZE_512 = "512"
  SIZE_1K = "1K"
  SIZE_2K = "2K"
  SIZE_4K = "4K"


def get_image_generation_tool(
    client: genai.Client, model: str = sdk_types.DEFAULT_IMAGE_GENERATION_MODEL
):
  """Returns a tool function for generating images.

  Args:
      client: The shared genai.Client instance.
      model: The model to use for generation. Defaults to
        'gemini-3.1-flash-image-preview'.
  """

  @pydantic.validate_call
  async def generate_image(
      prompt: str,
      output_path: str | None = None,
      aspect_ratio: AspectRatio | None = None,
      image_size: ImageSize | None = None,
  ) -> types.Part | dict[str, Any]:
    """Generates an image from a text prompt.

    Args:
        prompt: A highly detailed instruction for the image model. Must follow
          the structure of Scene -> Subject -> Details -> Aesthetic Constraints.
          Include explicit quality levers.
        output_path: Optional file path to save the image to disk.
        aspect_ratio: Optional aspect ratio. Defaults to '1:1'.
        image_size: Optional resolution. Defaults to '1K'.

    Returns:
        The generated image data (as a multi-modal Part or dict). If output_path
        was provided, the image is also saved to that location.
    """
    generation_config = {}
    if aspect_ratio or image_size:
      image_config = {}
      if aspect_ratio:
        image_config["aspect_ratio"] = aspect_ratio.value
      if image_size:
        image_config["image_size"] = image_size.value
      generation_config["image_config"] = image_config

    try:
      interaction: interactions.Interaction = (
          await client.aio.interactions.create(
              model=model,
              input=prompt,
              response_modalities=["image"],
              generation_config=generation_config
              if generation_config
              else None,
              stream=False,
          )
      )

      image_bytes = None
      mime_type = "image/png"  # Default fallback

      for output in interaction.outputs:
        if output.type == "image":
          image_bytes = base64.b64decode(output.data)
          mime_type = output.mime_type
          break

      if not image_bytes:
        raise ValueError("No image data returned by the model.")

      if output_path:
        workspace_root = os.environ.get("BUILD_WORKING_DIRECTORY", os.getcwd())
        full_path = os.path.abspath(os.path.join(workspace_root, output_path))
        if not full_path.startswith(os.path.abspath(workspace_root)):
          raise ValueError(
              f"Path must be within the base directory: {workspace_root}"
          )
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
          f.write(image_bytes)

      # Return a Part object as requested
      return types.Part(
          inline_data=types.Blob(data=image_bytes, mime_type=mime_type)
      )

    except ValueError as e:
      raise e
    except Exception as e:
      raise RuntimeError(f"Failed to generate image: {e}") from e

  generate_image.__name__ = "generate_image"
  return generate_image
