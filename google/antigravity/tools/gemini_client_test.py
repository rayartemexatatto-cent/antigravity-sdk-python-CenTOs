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

"""Tests for gemini_client."""

from unittest import mock

from absl.testing import absltest
from google import genai

from google.antigravity import types
from google.antigravity.tools import gemini_client


class GeminiClientTest(absltest.TestCase):

  @mock.patch.object(genai, "Client", autospec=True)
  def test_get_gemini_client_with_config(self, mock_client_class):
    """Verifies that get_gemini_client passes config correctly.

    What: Verifies that GeminiConfig is passed to genai.Client.
    Why: Ensures that structured configuration is used for authentication.
    How: Asserts that mock_client_class was called with config values.

    Args:
      mock_client_class: The mocked genai.Client class.
    """
    config = types.GeminiConfig(
        api_key="test_key",
    )
    gemini_client.get_gemini_client(config=config)
    mock_client_class.assert_called_once_with(
        api_key="test_key",
    )

  @mock.patch.object(genai, "Client", autospec=True)
  def test_get_gemini_client_without_config(self, mock_client_class):
    """Verifies that get_gemini_client uses defaults when no config provided.

    What: Verifies that default config is used when none is passed.
    Why: Ensures that the client falls back to environment variables via
      GeminiConfig defaults.
    How: Asserts that mock_client_class was called with default values.

    Args:
      mock_client_class: The mocked genai.Client class.
    """
    gemini_client.get_gemini_client()
    mock_client_class.assert_called_once_with(
        api_key=None,
    )


if __name__ == "__main__":
  absltest.main()
