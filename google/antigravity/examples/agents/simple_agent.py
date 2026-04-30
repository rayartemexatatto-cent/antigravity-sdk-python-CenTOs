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

"""Simple agent example using the high-level Agent API."""

import asyncio
import logging
from google.antigravity.agent import Agent


async def main():
  logging.basicConfig(level=logging.INFO)

  print("Creating agent...")
  async with Agent(
      system_instructions="You are a helpful assistant.",
      read_only=True,
  ) as agent:

    print("\nChatting with agent...")
    response = await agent.chat("Hello! What is 2+2?")
    print(f"Agent: {response.text}\n")


if __name__ == "__main__":
  asyncio.run(main())
