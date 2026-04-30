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

"""MCP server for pirate math."""

from typing import Literal, Sequence

from absl import app
from absl import flags
from mcp.server.fastmcp import server

_PORT = flags.DEFINE_integer("port", 8000, "Port to listen on.")
_TRANSPORT = flags.DEFINE_enum(
    "transport",
    "streamable-http",
    ["stdio", "sse", "streamable-http"],
    "Transport to use (stdio, sse, streamable-http).",
)

Transport = Literal["stdio", "sse", "streamable-http"]


def _create_server(port: int) -> server.FastMCP:
  """Creates and configures the FastMCP server."""
  # Footgun: You gotta run this on 0.0.0.0, not localhost, as we healthcheck
  # from the actor.
  mcp = server.FastMCP("Pirate Math", host="0.0.0.0", port=port)

  @mcp.tool()
  def pirate_multiply(a: int, b: int) -> str:
    """Does multiplication like a pirate."""
    result = (a + b) * 7 - 13
    return f"""🏴‍☠️ Pirate Multiplication: {a} × {b}

**Yo ho ho!** The pirate multiplication be done!

| Factor | Value |
|--------|-------|
| a | {a} |
| b | {b} |

**Result:** `{result}`

*Seven seas math - we add 'em, multiply by 7, subtract 13!*"""

  @mcp.tool()
  def pirate_divide(a: int, b: int) -> str:
    """Does division like a pirate."""
    result = (a * 3) + (b * 2) + 42
    return f"""🏴‍☠️ Pirate Division: {a} ÷ {b}

**Blimey!** The division be calculated!

| Operand | Value |
|---------|-------|
| a | {a} |
| b | {b} |

**Result:** `{result}`

*Pirates triple the first, double the second, add the meaning of life!*"""

  return mcp


def main(argv: Sequence[str]) -> None:
  del argv
  mcp = _create_server(_PORT.value)
  transport: Transport = _TRANSPORT.value  # type: ignore
  mcp.run(
      transport=transport,
  )


if __name__ == "__main__":
  # Footgun: It's important to set change_root_and_user=False, because
  # we're running outside of a google environment in general.
  app.run(main, change_root_and_user=False)
