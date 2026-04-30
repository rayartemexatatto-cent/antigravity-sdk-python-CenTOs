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

"""Unit tests for bridge.py."""

import asyncio
import unittest
from unittest import mock
from mcp import types
from mcp.client.session_group import ClientSessionGroup
from google.antigravity.mcp.bridge import McpBridge
from google.antigravity.mcp.bridge import register_mcp_tools
from google.antigravity.tools.tool_runner import ToolRunner


class TestBridge(unittest.TestCase):

  def test_register_mcp_tools(self):
    mock_tool_runner = mock.MagicMock(spec=ToolRunner)

    mock_session_group = mock.MagicMock(spec=ClientSessionGroup)
    mock_tool = types.Tool(
        name="test_tool",
        description="A test tool",
        inputSchema={"type": "object"},
    )
    mock_session_group.tools = {"test_tool": mock_tool}
    mock_session_group.call_tool = mock.AsyncMock(return_value="tool_result")

    async def run_test():
      registered_wrappers = await register_mcp_tools(
          mock_tool_runner, mock_session_group
      )

      mock_tool_runner.register.assert_called_once()
      args, kwargs = mock_tool_runner.register.call_args

      wrapper_fn = args[0]
      self.assertEqual(kwargs["name"], "test_tool")
      self.assertEqual(wrapper_fn.__doc__, "A test tool")

      self.assertEqual(len(registered_wrappers), 1)
      self.assertEqual(registered_wrappers[0], wrapper_fn)

      result = await wrapper_fn(arg1="val1")
      self.assertEqual(result, "tool_result")
      mock_session_group.call_tool.assert_called_once_with(
          "test_tool", {"arg1": "val1"}
      )

    asyncio.run(run_test())


class TestMcpBridge(unittest.TestCase):

  def test_connect_stdio(self):
    """Verifies that connect_stdio correctly configures stdio transport."""
    mock_tool_runner = mock.MagicMock(spec=ToolRunner)
    bridge = McpBridge(mock_tool_runner)

    patch_target = (
        "google.antigravity.mcp.bridge.ClientSessionGroup"
    )
    with mock.patch(patch_target) as mock_group_cls:
      mock_session_group = mock.MagicMock(spec=ClientSessionGroup)
      mock_group_cls.return_value = mock_session_group
      mock_session_group.__aenter__ = mock.AsyncMock(
          return_value=mock_session_group
      )
      mock_session_group.connect_to_server = mock.AsyncMock()
      mock_session_group.tools = {}

      async def run_test():
        await bridge.connect_stdio("pirate_command", ["--transport=stdio"])
        mock_session_group.connect_to_server.assert_called_once()

      asyncio.run(run_test())

  def test_connect_sse(self):
    """Verifies that connect_sse correctly configures SSE transport parameters."""
    mock_tool_runner = mock.MagicMock(spec=ToolRunner)
    bridge = McpBridge(mock_tool_runner)

    patch_target = (
        "google.antigravity.mcp.bridge.ClientSessionGroup"
    )
    with mock.patch(patch_target) as mock_group_cls:
      mock_session_group = mock.MagicMock(spec=ClientSessionGroup)
      mock_group_cls.return_value = mock_session_group
      mock_session_group.__aenter__ = mock.AsyncMock(
          return_value=mock_session_group
      )
      mock_session_group.connect_to_server = mock.AsyncMock()
      mock_session_group.tools = {}

      async def run_test():
        await bridge.connect_sse("http://localhost:8080/sse")
        mock_session_group.connect_to_server.assert_called_once()

      asyncio.run(run_test())

  def test_stop(self):
    """Verifies that McpBridge stopped safely exiting ClientSessionGroup contexts."""
    mock_tool_runner = mock.MagicMock(spec=ToolRunner)
    bridge = McpBridge(mock_tool_runner)

    patch_target = (
        "google.antigravity.mcp.bridge.ClientSessionGroup"
    )
    with mock.patch(patch_target) as mock_group_cls:
      mock_session_group = mock.MagicMock(spec=ClientSessionGroup)
      mock_group_cls.return_value = mock_session_group
      mock_session_group.__aenter__ = mock.AsyncMock(
          return_value=mock_session_group
      )
      mock_session_group.__aexit__ = mock.AsyncMock()
      mock_session_group.connect_to_server = mock.AsyncMock()
      mock_session_group.tools = {}

      async def run_test():
        await bridge.connect_stdio("pirate_command", ["--transport=stdio"])
        await bridge.stop()
        mock_session_group.__aexit__.assert_called_once()

      asyncio.run(run_test())


if __name__ == "__main__":
  unittest.main()
