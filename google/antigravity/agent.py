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

"""Tier 1 API for Antigravity SDK."""

import asyncio
import logging
from typing import Any, Callable

from google.antigravity import types
from google.antigravity.connections import local_connection
from google.antigravity.connections.local_connection import LocalConnectionStrategy
from google.antigravity.conversation import conversation
from google.antigravity.hooks import cli
from google.antigravity.hooks import hook_runner
from google.antigravity.hooks import hooks
from google.antigravity.hooks import policy
from google.antigravity.mcp import bridge
from google.antigravity.tools import tool_runner
from google.antigravity.triggers import trigger_runner
from google.antigravity.triggers import triggers as triggers_lib


class Agent:
  """High-level Agent API for simplified interaction."""

  def __init__(
      self,
      system_instructions: str | types.SystemInstructions,
      tools: list[Callable[..., Any]] | None = None,
      model: str = types.DEFAULT_MODEL,
      api_key: str | None = None,
      read_only: bool = True,
      policies: list[policy.Policy] | None = None,
      hooks_list: list[hooks.Hook] | None = None,
      triggers: list[triggers_lib.Trigger] | None = None,
      mcp_servers: list[dict[str, Any]] | None = None,
      workspaces: list[str] | None = None,
  ):
    """Initializes the Agent.

    Args:
        system_instructions: System instructions for the agent. If a string is
          passed, it will be appended to the default system instructions. Use
          `types.CustomSystemInstructions` to completely replace them.
        tools: Custom Python tools to register.
        model: Gemini model name.
        api_key: API key for Gemini API.
        read_only: If True, only read-only builtin tools are enabled.
        policies: Custom policies to enforce.
        hooks_list: Custom hooks to register. Should be instances of hook
          classes defined in `hooks.py`.
        triggers: Custom triggers to register. Should be async functions taking
          TriggerContext.
        mcp_servers: MCP server configurations. List of dicts, e.g., `[{"type":
          "stdio", "command": "cmd", "args": []}]` or `[{"type": "sse", "url":
          "url"}]`.
        workspaces: List of directory paths to restrict the agent to.
    """
    self.system_instructions = system_instructions
    self.tools = tools or []
    self.model = model
    self.api_key = api_key
    self.read_only = read_only
    self.policies = policies or []
    self.hooks_list = hooks_list or []
    self.triggers = triggers or []
    self.mcp_servers = mcp_servers or []
    self.workspaces = workspaces or []
    self._strategy = None
    self._conversation = None
    self._conversation_cm = None
    self._tool_runner = None
    self._hook_runner = None
    self._trigger_runner = None
    self._mcp_bridge = None
    self._pending_hooks = list(self.hooks_list)
    self._pending_triggers = list(self.triggers)

  def register_hook(self, hook: hooks.Hook):
    """Registers a hook by inferring its type."""
    if not self._hook_runner:
      self._pending_hooks.append(hook)
      return
    self._hook_runner.register_hook(hook)

  def register_trigger(self, trigger: triggers_lib.Trigger):
    """Registers a trigger.

    Cannot be called after the agent has started.

    Args:
      trigger: The trigger function to register.

    Raises:
      RuntimeError: If the agent has already started.
    """
    if self._conversation:
      raise RuntimeError(
          "Cannot register triggers after the agent has started."
      )
    self._pending_triggers.append(trigger)

  async def __aenter__(self) -> "Agent":
    """Starts the agent session."""
    logging.info("Starting Agent session")
    try:
      self._tool_runner = tool_runner.ToolRunner(tools=self.tools)

      self._hook_runner = hook_runner.HookRunner()

      # Register pending hooks
      for hook in self._pending_hooks:
        self._hook_runner.register_hook(hook)
      self._pending_hooks.clear()

      # Apply policies
      active_policies = list(self.policies)
      if not self.read_only and not active_policies:
        raise ValueError(
            "Policies must be provided when read_only is False to prevent "
            "interactive handlers from hanging in non-interactive contexts."
        )

      if active_policies:
        self._hook_runner.pre_tool_call_decide_hooks.append(
            policy.enforce(active_policies)
        )

      # Connect MCP servers
      if self.mcp_servers:
        logging.info("Connecting to MCP servers...")
        self._mcp_bridge = bridge.McpBridge(self._tool_runner)
        for server_cfg in self.mcp_servers:
          srv_type = server_cfg.get("type")
          if srv_type == "stdio":
            await self._mcp_bridge.connect_stdio(
                server_cfg["command"], server_cfg.get("args", [])
            )
          elif srv_type == "sse":
            await self._mcp_bridge.connect_sse(
                server_cfg["url"], server_cfg.get("headers")
            )
          else:
            raise ValueError(f"Unknown MCP server type: {srv_type}")

      if self.read_only:
        capabilities_config = types.CapabilitiesConfig(
            enabled_tools=types.BuiltinTools.read_only()
        )
      else:
        capabilities_config = types.CapabilitiesConfig()

      if isinstance(self.system_instructions, str):
        si = types.TemplatedSystemInstructions(
            sections=[
                types.SystemInstructionSection(content=self.system_instructions)
            ]
        )
      else:
        si = self.system_instructions

      self._strategy = local_connection.LocalConnectionStrategy(
          tool_runner=self._tool_runner,
          hook_runner=self._hook_runner,
          gemini_config=types.GeminiConfig(
              model_name=self.model, api_key=self.api_key
          ),
          system_instructions=si,
          capabilities_config=capabilities_config,
          workspaces=self.workspaces,
      )

      logging.info("Starting connection and creating conversation...")
      self._conversation_cm = conversation.Conversation.create(self._strategy)
      self._conversation = await self._conversation_cm.__aenter__()

      # Register triggers
      if self._pending_triggers:
        logging.info("Registering triggers...")
        for trigger in self._pending_triggers:
          self._conversation.register_trigger(trigger)
        self._pending_triggers.clear()

      return self
    except Exception:
      logging.exception("Failed to start Agent session, cleaning up...")
      await self.__aexit__(None, None, None)
      raise

  async def __aexit__(self, exc_type, exc_val, exc_tb):
    """Stops the agent session."""
    logging.info("Stopping Agent session")
    if self._mcp_bridge:
      await self._mcp_bridge.stop()
    if self._conversation_cm:
      await self._conversation_cm.__aexit__(exc_type, exc_val, exc_tb)

  async def chat(self, prompt: str) -> types.ChatResponse:
    """Sends a prompt and returns the final response."""
    if not self._conversation:
      raise RuntimeError(
          "Agent session not started. Use 'async with Agent(...)'."
      )
    return await self._conversation.chat(prompt)

  async def run_interactive_loop(self):
    """Runs an interactive CLI loop."""
    if not self._conversation:
      raise RuntimeError(
          "Agent session not started. Use 'async with Agent(...)'."
      )

    self._hook_runner.on_interaction_hooks.append(cli.AskQuestionHook())
    print("Starting interactive loop. Type 'exit' or 'quit' to end.")
    while True:
      try:
        user_input = await asyncio.to_thread(input, "User: ")
        user_input = user_input.strip()
        if not user_input:
          continue
        if user_input.lower() in ("exit", "quit"):
          print("Goodbye!")
          break

        await self._conversation.send(user_input)

        async for step in self._conversation.receive_steps():
          if step.is_final_response:
            print(f"Agent: {step.content}")

      except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
        break
      except Exception as e:  # pylint: disable=broad-exception-caught
        logging.exception("Error in interactive loop: %s", e)
        print(f"Error: {e}")
