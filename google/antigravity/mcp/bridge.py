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

"""Bridge between MCP services and the SDK ToolRunner."""

from typing import Any, Callable
from mcp.client import stdio
from mcp.client.session_group import ClientSessionGroup
from mcp.client.session_group import SseServerParameters
from google.antigravity.tools.tool_runner import ToolWithSchema


async def get_mcp_tools(
    session_group: ClientSessionGroup,
) -> list[ToolWithSchema]:
  """Fetches tools from session_group and returns them as ToolWithSchema.

  Args:
    session_group: The ClientSessionGroup to fetch tools from.

  Returns:
    A list of ToolWithSchema objects.
  """
  tools = []
  for tool_info in session_group.tools.values():
    name = tool_info.name

    def make_wrapper(tool_name: str, doc: str | None) -> Callable[..., Any]:
      async def wrapper(**kwargs: Any) -> Any:
        return await session_group.call_tool(tool_name, kwargs)

      wrapper.__name__ = tool_name
      if doc:
        wrapper.__doc__ = doc
      return wrapper

    wrapper_fn = make_wrapper(name, tool_info.description)
    tool_with_schema = ToolWithSchema(wrapper_fn, tool_info.inputSchema)
    tools.append(tool_with_schema)

  return tools


class McpBridge:
  """Simplifies the lifecycle of MCP Client Sessions."""

  def __init__(self):
    self.session_group = None
    self.tools: list[ToolWithSchema] = []

  async def connect_stdio(self, command: str, args: list[str]):
    """Connects to a local MCP server over stdio."""
    params = stdio.StdioServerParameters(command=command, args=args)
    await self._connect(params)

  async def connect_sse(self, url: str, headers: dict[str, str] | None = None):
    """Connects to a remote MCP server over SSE."""
    params = SseServerParameters(url=url, headers=headers)
    await self._connect(params)

  async def _connect(self, params):
    if not self.session_group:
      self.session_group = ClientSessionGroup()
      await self.session_group.__aenter__()
    await self.session_group.connect_to_server(params)
    self.tools = await get_mcp_tools(self.session_group)

  async def stop(self):
    """Cleans up all active MCP sessions."""
    if self.session_group:
      await self.session_group.__aexit__(None, None, None)
      self.session_group = None
