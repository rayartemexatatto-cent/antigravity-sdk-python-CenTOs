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

"""Utility for creating a unified Gemini API client."""

from google import genai
from google.antigravity import types


def get_gemini_client(
    config: types.GeminiConfig | None = None,
) -> genai.Client:
  """Returns a genai.Client instance based on provided configuration.

  Args:
      config: Optional GeminiConfig. If not provided, default configuration will
        be used (which falls back to environment variables).

  Returns:
      An initialized genai.Client.
  """
  if not config:
    config = types.GeminiConfig()

  return genai.Client(
      api_key=config.api_key,
  )
