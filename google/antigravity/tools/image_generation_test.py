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

"""Tests for image_generation tool."""

import base64
import unittest
from unittest import mock

from absl.testing import absltest
from google.genai import types
import pydantic

from google.antigravity.tools import image_generation


class ImageGenerationToolTest(unittest.IsolatedAsyncioTestCase):

  def setUp(self):
    super().setUp()
    self.mock_client = mock.MagicMock()
    self.tool = image_generation.get_image_generation_tool(self.mock_client)

  async def test_call_with_valid_params(self):
    """Tests calling the tool with valid parameters."""
    mock_interaction = mock.MagicMock()
    mock_output = mock.MagicMock()
    mock_output.type = "image"
    mock_output.data = base64.b64encode(b"image_bytes").decode("utf-8")
    mock_output.mime_type = "image/png"
    mock_interaction.outputs = [mock_output]
    self.mock_client.aio.interactions.create = mock.AsyncMock(
        return_value=mock_interaction
    )

    result = await self.tool(prompt="A beautiful cat")

    self.assertIsInstance(result, types.Part)
    self.assertEqual(result.inline_data.data, b"image_bytes")
    self.assertEqual(result.inline_data.mime_type, "image/png")

  async def test_call_with_invalid_aspect_ratio(self):
    """Tests that invalid aspect ratio raises error."""
    with self.assertRaises(pydantic.ValidationError):
      await self.tool(prompt="A cat", aspect_ratio="invalid")

  async def test_call_with_invalid_image_size(self):
    """Tests that invalid image size raises error."""
    with self.assertRaises(pydantic.ValidationError):
      await self.tool(prompt="A cat", image_size="invalid")

  async def test_call_missing_prompt(self):
    """Tests that missing prompt raises error."""
    with self.assertRaises(pydantic.ValidationError):
      await self.tool()

  async def test_call_with_invalid_output_path(self):
    """Tests that output path outside workspace raises error."""
    mock_interaction = mock.MagicMock()
    mock_output = mock.MagicMock()
    mock_output.type = "image"
    mock_output.data = base64.b64encode(b"image_bytes").decode("utf-8")
    mock_output.mime_type = "image/png"
    mock_interaction.outputs = [mock_output]
    self.mock_client.aio.interactions.create = mock.AsyncMock(
        return_value=mock_interaction
    )

    with self.assertRaisesRegex(
        ValueError, "Path must be within the base directory"
    ):
      await self.tool(prompt="A cat", output_path="/tmp/outside.png")

    with self.assertRaisesRegex(
        ValueError, "Path must be within the base directory"
    ):
      await self.tool(prompt="A cat", output_path="../outside.png")

  async def test_call_with_valid_aspect_ratio_and_size(self):
    """Tests that valid aspect ratio and size are passed to the API."""
    mock_interaction = mock.MagicMock()
    mock_output = mock.MagicMock()
    mock_output.type = "image"
    mock_output.data = base64.b64encode(b"image_bytes").decode("utf-8")
    mock_output.mime_type = "image/png"
    mock_interaction.outputs = [mock_output]
    self.mock_client.aio.interactions.create = mock.AsyncMock(
        return_value=mock_interaction
    )

    await self.tool(
        prompt="A cat",
        aspect_ratio=image_generation.AspectRatio.WIDE,
        image_size=image_generation.ImageSize.SIZE_1K,
    )

    self.mock_client.aio.interactions.create.assert_called_once()
    kwargs = self.mock_client.aio.interactions.create.call_args.kwargs
    self.assertIn("generation_config", kwargs)
    self.assertEqual(
        kwargs["generation_config"]["image_config"]["aspect_ratio"], "16:9"
    )
    self.assertEqual(
        kwargs["generation_config"]["image_config"]["image_size"], "1K"
    )

  async def test_call_no_image_data(self):
    """Tests that error is raised when no image data is returned."""
    mock_interaction = mock.MagicMock()
    mock_output = mock.MagicMock()
    mock_output.type = "text"
    mock_output.text = "Sorry, I cannot generate an image."
    mock_interaction.outputs = [mock_output]
    self.mock_client.aio.interactions.create = mock.AsyncMock(
        return_value=mock_interaction
    )

    with self.assertRaisesRegex(
        ValueError, "No image data returned by the model"
    ):
      await self.tool(prompt="A cat")

  @mock.patch("os.makedirs")
  @mock.patch("builtins.open", new_callable=mock.mock_open)
  @mock.patch.dict("os.environ", {"BUILD_WORKING_DIRECTORY": "/workspace"})
  async def test_call_with_valid_output_path(
      self, mock_open, mock_makedirs
  ):

    mock_interaction = mock.MagicMock()
    mock_output = mock.MagicMock()
    mock_output.type = "image"
    mock_output.data = base64.b64encode(b"image_bytes").decode("utf-8")
    mock_output.mime_type = "image/png"
    mock_interaction.outputs = [mock_output]
    self.mock_client.aio.interactions.create = mock.AsyncMock(
        return_value=mock_interaction
    )

    await self.tool(prompt="A cat", output_path="output/cat.png")

    mock_makedirs.assert_called_once_with("/workspace/output", exist_ok=True)
    mock_open.assert_called_once_with("/workspace/output/cat.png", "wb")
    mock_open().write.assert_called_once_with(b"image_bytes")

  async def test_call_unexpected_exception(self):
    """Tests that unexpected exceptions are wrapped in RuntimeError."""
    self.mock_client.aio.interactions.create = mock.AsyncMock(
        side_effect=Exception("Unexpected failure")
    )

    with self.assertRaisesRegex(
        RuntimeError, "Failed to generate image: Unexpected failure"
    ):
      await self.tool(prompt="A cat")


if __name__ == "__main__":
  absltest.main()
