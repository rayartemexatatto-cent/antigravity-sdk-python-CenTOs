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

"""Builtin CLI hooks for interactive and policy-governed agent execution.

This module provides ready-to-use hooks for asking the user for confirmation
before executing tools and for answering multiple-choice or write-in questions.
"""

import asyncio
from typing import Any

from google.antigravity import types
from google.antigravity.hooks import hooks


class ToolConfirmationHook(hooks.PreToolCallDecideHook):
  """Hook that prompts the user for confirmation before executing a tool."""

  async def run(
      self, context: hooks.HookContext, data: types.ToolCall
  ) -> hooks.HookResult:
    """Asks the user for confirmation via standard input.

    Args:
      context: The hook context.
      data: The tool call requested by the agent.

    Returns:
      A HookResult indicating whether to allow or deny execution.
    """
    print(f"\nTool execution requested: {data.name}")
    if data.args:
      print(f"Arguments: {data.args}")

    try:
      ans = await asyncio.to_thread(input, "Allow execution? (y/n) [n]: ")
    except EOFError:
      ans = "n"

    if ans.strip().lower() in ("y", "yes"):
      return hooks.HookResult(allow=True)
    return hooks.HookResult(allow=False, message="User denied tool call.")


async def ask_user_handler(tc: types.ToolCall) -> bool:
  """Prompts the user for confirmation before executing a tool.

  This is a convenient handler for use with the policy system.

  Args:
    tc: The tool call requested by the agent.

  Returns:
    True if the user allows execution, False otherwise.
  """
  print(f"\nPolicy check: Tool execution requested: {tc.name}")
  if tc.args:
    print(f"Arguments: {tc.args}")

  try:
    ans = await asyncio.to_thread(input, "Allow execution? (y/n) [n]: ")
  except EOFError:
    ans = "n"

  return ans.strip().lower() in ("y", "yes")


class AskQuestionHook(hooks.OnInteractionHook):
  """Hook that prompts the user to answer questions asked by the agent."""

  async def run(
      self, context: hooks.HookContext, interaction_spec: Any
  ) -> hooks.QuestionHookResult:
    """Asks the user for answers to each question via standard input.

    Args:
      context: The hook context.
      interaction_spec: The list of AskQuestionEntry objects (expected to be a
        list).

    Returns:
      A QuestionHookResult containing the user's responses.
    """
    questions = interaction_spec
    responses = []
    try:
      for q in questions:
        print(f"\nQuestion: {q.question}")
        options = list(q.options) if hasattr(q, "options") else []
        for idx, opt in enumerate(options):
          print(f"  {idx + 1}. {opt.text}")

        ans = await asyncio.to_thread(input, "Response: ")
        ans = ans.strip()
        if not ans:
          responses.append(hooks.QuestionResponse(skipped=True))
          continue

        # Try to match by option number
        matched_id = None
        if options:
          try:
            selected_idx = int(ans) - 1
            if 0 <= selected_idx < len(options):
              matched_id = options[selected_idx].id
          except ValueError:
            pass

          # Try to match by exact option text or ID
          if not matched_id:
            for opt in options:
              if (
                  ans.lower() == opt.text.lower()
                  or ans.lower() == opt.id.lower()
              ):
                matched_id = opt.id
                break

        if matched_id:
          responses.append(
              hooks.QuestionResponse(selected_option_ids=[matched_id])
          )
        else:
          responses.append(hooks.QuestionResponse(freeform_response=ans))

    except EOFError:
      return hooks.QuestionHookResult(responses=responses, cancelled=True)

    return hooks.QuestionHookResult(responses=responses)
