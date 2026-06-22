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

"""Layer 1 API for Antigravity SDK."""

import contextlib
import logging
from typing import cast

from google.antigravity import types
from google.antigravity.connections import connection as connection_module
from google.antigravity.conversation import conversation
from google.antigravity.hooks import hook_runner
from google.antigravity.hooks import policy
from google.antigravity.tools import tool_context
from google.antigravity.tools import tool_runner
from google.antigravity.triggers import trigger_runner

__all__ = ["Agent"]
class Agent:
  """High-level Agent API for simplified interaction."""

  def __init__(self, config: connection_module.AgentConfig):
    """Initializes the Agent.
    Args:
        config: Declarative agent configuration.
    """
    self._config = config.model_copy(deep=True)
    if self._config.response_schema:
      # The response_schema is validated/stringified in AgentConfig.
      self._config.capabilities.finish_tool_schema_json = cast(
          str, self._config.response_schema
      )
    self._strategy = None
    self._conversation = None
    self._tool_runner = None
    self._hook_runner = None
    self._trigger_runner = None
    # Use the original config (not self._config) for hooks and triggers:
    # model_copy(deep=True) creates new objects, breaking reference equality
    # for user-provided hooks/triggers. The list() snapshot prevents the
    # caller from mutating our copy, while preserving object identity.
    self._pending_hooks = list(config.hooks)
    self._pending_triggers = list(config.triggers)
    self._exit_stack = contextlib.AsyncExitStack()

  async def __aenter__(self) -> "Agent":
    """Starts the agent session.

    Returns:
        The started Agent instance.
    """
    logging.info("Starting Agent session")
    try:
      self._hook_runner = hook_runner.HookRunner()

      # Register pending hooks
      for hook in self._pending_hooks:
        self._hook_runner.register_hook(hook)
      self._pending_hooks.clear()

      # Apply policies
      active_policies = list(self._config.policies)
      cfg = self._config.capabilities
      read_only_tools = set(types.BuiltinTools.read_only())
      # enabled_tools and disabled_tools are mutually exclusive
      # (enforced by CapabilitiesConfig validation).
      if cfg.enabled_tools is not None:
        active_tools = set(cfg.enabled_tools)
      elif cfg.disabled_tools is not None:
        active_tools = set(types.BuiltinTools) - set(cfg.disabled_tools)
      else:
        active_tools = set(types.BuiltinTools)
      has_write_tools = bool(active_tools - read_only_tools)
      has_mcp_servers = bool(self._config.mcp_servers)
      has_tool_decide_hook = bool(self._hook_runner.pre_tool_call_decide_hooks)

      if (
          (has_write_tools or has_mcp_servers)
          and not active_policies
          and not has_tool_decide_hook
      ):
        raise ValueError(
            "Write tools or MCP servers are enabled without a safety policy. "
            "Add policies=[policy.allow_all()] to approve all tool calls, "
            "or policies=[policy.deny_all(), policy.allow('tool_name')] "
            "to selectively allow specific tools."
        )

      if active_policies:
        self._hook_runner.register_hook(
            policy.enforce(
                active_policies, mcp_servers=self._config.mcp_servers
            )
        )

      all_tools = list(self._config.tools)
      self._tool_runner = tool_runner.ToolRunner(tools=all_tools)

      self._strategy = self._config.create_strategy(
          tool_runner=self._tool_runner,
          hook_runner=self._hook_runner,
      )

      logging.info("Starting connection and creating conversation...")
      self._conversation = await self._exit_stack.enter_async_context(
          conversation.Conversation.create(self._strategy)
      )

      # Start triggers via TriggerRunner.
      if self._pending_triggers:
        logging.info("Starting triggers...")
        self._trigger_runner = await self._exit_stack.enter_async_context(
            trigger_runner.TriggerRunner(
                triggers=list(self._pending_triggers),
                connection=self.conversation.connection,
            )
        )
        self._pending_triggers.clear()

      # Wire ToolContext into ToolRunner so tools can access
      # conversation capabilities (same pattern as TriggerRunner).
      if self._tool_runner:
        ctx = tool_context.ToolContext(self.conversation)
        self._tool_runner.set_context(ctx)

      return self
    except Exception:
      logging.exception("Failed to start Agent session, cleaning up...")
      await self._exit_stack.aclose()
      raise

  async def __aexit__(self, exc_type, exc_val, exc_tb):
    """Stops the agent session.

    Args:
        exc_type: The exception type, if any.
        exc_val: The exception value, if any.
        exc_tb: The traceback, if any.
    """
    logging.info("Stopping Agent session")
    return await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)

  async def chat(self, prompt: types.Content) -> types.ChatResponse:
    """Sends a prompt and returns the final response.

    Args:
        prompt: The user prompt or content to send.

    Returns:
        The final response from the agent.
    """
    return await self.conversation.chat(prompt)

  @property
  def is_started(self) -> bool:
    """Whether the agent session has been started."""
    return self._conversation is not None

  @property
  def conversation(self) -> conversation.Conversation:
    """Returns the active Conversation session.

    Use this for advanced session introspection: history, turn count,
    compaction indices, usage, or direct send/receive_steps control.
    For most use cases, prefer chat() instead.

    Raises:
      RuntimeError: If the agent session has not been started.
    """
    if not self._conversation:
      raise RuntimeError(
          "Agent session not started. Use 'async with Agent(...)'."
      )
    return self._conversation

  @property
  def conversation_id(self) -> str | None:
    """Returns the conversation identifier assigned by the runtime.

    Available after the session has started and at least one message has
    been exchanged.  Pass this value back via SessionConfig.conversation_id
    to resume from a saved session.  Returns None before the session starts.
    """
    if not self._conversation:
      return None
    return self._conversation.conversation_id or None
from google.antigravity.hooks import policy
from google.antigravity import LocalAgentConfig, Agent
import asyncio

# =====================================================================
# GANCHO 1: DECIDE HOOK (Seguridad para Localhost)
# =====================================================================
async def bloquear_ejecucion_externa(tool_call, context):
    """
    Evita que el agente ejecute comandos en entornos que no sean localhost
    o que alteren puertos no autorizados en tu mesa de control.
    """
    argumentos = str(tool_call.arguments)
    
    # Si intenta usar herramientas del sistema fuera de tu red local, bloqueamos
    if "run_command" in tool_call.name and "127.0.0.1" not in argumentos and "localhost" not in argumentos:
        print(f"⚠️ Intento de comando externo detectado en: {tool_call.name}")
        return {"allow": False} # S_S8: Decide hooks devuelven allow=True/False
        
    return {"allow": True}

# =====================================================================
# GANCHO 2: TRANSFORM HOOK (Autocorrección de Puertos y Protocolos)
# =====================================================================
async def corregir_errores_localhost(tool_error, context):
    """
    Si el agente intenta levantar un servidor local y choca con un puerto
    en uso o un error de protocolo, interceptamos el fallo y le inyectamos 
    la solución exacta de tus documentos de Drive para que se auto-corrija.
    """
    mensaje_error = str(tool_error.error)
    print(f"🔍 Interceptando error de herramienta: {mensaje_error}")

    # Si detecta que el puerto 8181 está caído (como en tus configs locales)
    if "8181" in mensaje_error or "connection refused" in mensaje_error:
        solucion = (
            "\n ERROR DE PUERTO DETECTADO. "
            "Sugerencia de solución: El puerto 8181 de localhost está cerrado. "
            "Usa la herramienta ADB para mapear el reenvío: 'adb reverse tcp:8181 tcp:8181' "
            "y vuelve a intentar la conexión."
        )
        # S_S8: Transform hooks modifican el dato en tránsito y lo devuelven
        tool_error.error = f"{mensaje_error}\n{solucion}"
        print("⚡ Solución de puerto inyectada en el flujo de la IA.")

    return tool_error
async def ejecutar_agente_con_habilidades():
    # Creamos la configuración inyectando nuestros ganchos personalizados
    config = LocalAgentConfig(
        project="tu-proyecto-gcp",
        location="us-central1",
        # Registramos los ganchos que acabamos de escribir
        hooks=[bloquear_ejecucion_externa, corregir_errores_localhost],
        # Definimos políticas de herramientas obligatorias para habilitar escrituras
        policies=[policy.allow_all()] 
    )

    # El bloque "async with" ejecuta de fondo el __aenter__ de tu código,
    # levantando la sesión con los ganchos ya activos y validados.
    async with Agent(config) as agent:
        # El agente ahora es capaz de explorar y auto-corregir sus herramientas locales
        prompt = (
            "Intenta levantar el servicio de inventario en http://localhost:8181. "
            "Si falla, busca cómo resolverlo y restáuralo."
        )
        response = await agent.chat(prompt)
        print("\n:")
        print(await response.text())

if __name__ == "__main__":
    asyncio.run(ejecutar_agente_con_habilidades())

