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

"""Tests for builtin CLI hooks."""

import asyncio
import unittest
from unittest import mock

from google.antigravity import types
from google.antigravity.hooks import cli
from google.antigravity.hooks import hooks


class MockQuestion:

  def __init__(self, question, options=None):
    self.question = question
    self.options = options or []


class MockOption:

  def __init__(self, opt_id, text):
    self.id = opt_id
    self.text = text


class CliHooksTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(self.loop)
    self.ctx = hooks.HookContext()

  def tearDown(self):
    super().tearDown()
    self.loop.close()
    asyncio.set_event_loop(None)

  @mock.patch("builtins.input")
  def test_tool_confirmation_hook_allow(self, mock_input):
    """Verifies that the hook allows execution when the user confirms.

    What: Tests ToolConfirmationHook with 'y' input.
    Why: Ensures positive confirmation allows tool execution.
    How: Asserts that the returned HookResult has allow=True.

    Args:
      mock_input: The patched builtins.input function.
    """
    mock_input.return_value = "y"
    hook = cli.ToolConfirmationHook()
    tool_call = types.ToolCall(name="test_tool", args={"foo": "bar"})
    res = self.loop.run_until_complete(hook.run(self.ctx, tool_call))
    self.assertTrue(res.allow)

  @mock.patch("builtins.input")
  def test_tool_confirmation_hook_deny(self, mock_input):
    """Verifies that the hook denies execution when the user declines.

    What: Tests ToolConfirmationHook with 'n' input.
    Why: Ensures negative confirmation blocks tool execution.
    How: Asserts that the returned HookResult has allow=False.

    Args:
      mock_input: The patched builtins.input function.
    """
    mock_input.return_value = "n"
    hook = cli.ToolConfirmationHook()
    tool_call = types.ToolCall(name="test_tool", args={})
    res = self.loop.run_until_complete(hook.run(self.ctx, tool_call))
    self.assertFalse(res.allow)
    self.assertEqual(res.message, "User denied tool call.")

  @mock.patch("builtins.input")
  def test_tool_confirmation_hook_eof(self, mock_input):
    """Verifies that the hook denies execution on EOFError.

    What: Tests ToolConfirmationHook when input raises EOFError.
    Why: Ensures non-interactive execution defaults to denial.
    How: Asserts that the returned HookResult has allow=False.

    Args:
      mock_input: The patched builtins.input function.
    """
    mock_input.side_effect = EOFError
    hook = cli.ToolConfirmationHook()
    tool_call = types.ToolCall(name="test_tool", args={})
    res = self.loop.run_until_complete(hook.run(self.ctx, tool_call))
    self.assertFalse(res.allow)

  @mock.patch("builtins.input")
  def test_ask_question_hook_option_number(self, mock_input):
    """Verifies that the user can select an option by its index.

    What: Tests AskQuestionHook when the user inputs a 1-based index.
    Why: Ensures convenient selection for multiple-choice questions.
    How: Asserts that the response contains the correct option ID.

    Args:
      mock_input: The patched builtins.input function.
    """
    mock_input.return_value = "1"
    hook = cli.AskQuestionHook()
    q = MockQuestion(
        question="Choose?",
        options=[
            MockOption(opt_id="opt1", text="Option 1"),
            MockOption(opt_id="opt2", text="Option 2"),
        ],
    )
    session_ctx = hooks.SessionContext()
    turn_ctx = hooks.TurnContext(session_ctx)
    op_ctx = hooks.OperationContext(turn_ctx)
    res = self.loop.run_until_complete(hook.run(op_ctx, [q]))
    self.assertEqual(len(res.responses), 1)
    self.assertEqual(res.responses[0].selected_option_ids, ["opt1"])

  @mock.patch("builtins.input")
  def test_ask_question_hook_option_text(self, mock_input):
    """Verifies that the user can select an option by its exact text.

    What: Tests AskQuestionHook when the user inputs the text of an option.
    Why: Ensures robust matching when users type the answer directly.
    How: Asserts that the response contains the correct option ID.

    Args:
      mock_input: The patched builtins.input function.
    """
    mock_input.return_value = "Option 2"
    hook = cli.AskQuestionHook()
    q = MockQuestion(
        question="Choose?",
        options=[
            MockOption(opt_id="opt1", text="Option 1"),
            MockOption(opt_id="opt2", text="Option 2"),
        ],
    )
    session_ctx = hooks.SessionContext()
    turn_ctx = hooks.TurnContext(session_ctx)
    op_ctx = hooks.OperationContext(turn_ctx)
    res = self.loop.run_until_complete(hook.run(op_ctx, [q]))
    self.assertEqual(len(res.responses), 1)
    self.assertEqual(res.responses[0].selected_option_ids, ["opt2"])

  @mock.patch("builtins.input")
  def test_ask_question_hook_write_in(self, mock_input):
    """Verifies that the user can provide a write-in response.

    What: Tests AskQuestionHook for open-ended questions.
    Why: Ensures support for non-multiple-choice inputs.
    How: Asserts that the response contains the write-in text.

    Args:
      mock_input: The patched builtins.input function.
    """
    mock_input.return_value = "custom answer"
    hook = cli.AskQuestionHook()
    q = MockQuestion(question="What?")
    session_ctx = hooks.SessionContext()
    turn_ctx = hooks.TurnContext(session_ctx)
    op_ctx = hooks.OperationContext(turn_ctx)
    res = self.loop.run_until_complete(hook.run(op_ctx, [q]))
    self.assertEqual(len(res.responses), 1)
    self.assertEqual(res.responses[0].freeform_response, "custom answer")

  @mock.patch("builtins.input")
  def test_ask_question_hook_skip(self, mock_input):
    """Verifies that the user can skip a question by providing empty input.

    What: Tests AskQuestionHook with empty string input.
    Why: Ensures optional questions can be bypassed gracefully.
    How: Asserts that the response has skipped=True.

    Args:
      mock_input: The patched builtins.input function.
    """
    mock_input.return_value = ""
    hook = cli.AskQuestionHook()
    q = MockQuestion(question="What?")
    session_ctx = hooks.SessionContext()
    turn_ctx = hooks.TurnContext(session_ctx)
    op_ctx = hooks.OperationContext(turn_ctx)
    res = self.loop.run_until_complete(hook.run(op_ctx, [q]))
    self.assertEqual(len(res.responses), 1)
    self.assertTrue(res.responses[0].skipped)

  @mock.patch("builtins.input")
  def test_ask_question_hook_eof(self, mock_input):
    """Verifies that EOFError results in a skipped question.

    What: Tests AskQuestionHook when input raises EOFError.
    Why: Ensures non-interactive execution does not crash.
    How: Asserts that the response has skipped=True.

    Args:
      mock_input: The patched builtins.input function.
    """
    mock_input.side_effect = EOFError
    hook = cli.AskQuestionHook()
    q = MockQuestion(question="What?")
    session_ctx = hooks.SessionContext()
    turn_ctx = hooks.TurnContext(session_ctx)
    op_ctx = hooks.OperationContext(turn_ctx)
    res = self.loop.run_until_complete(hook.run(op_ctx, [q]))
    self.assertFalse(res.responses)
    self.assertTrue(res.cancelled)


class AskUserHandlerTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(self.loop)

  def tearDown(self):
    super().tearDown()
    self.loop.close()
    asyncio.set_event_loop(None)

  @mock.patch("builtins.input")
  def test_ask_user_handler_allow(self, mock_input):
    """Verifies that the handler returns True when the user confirms."""
    mock_input.return_value = "y"
    tc = types.ToolCall(name="test_tool", args={"key": "val"})
    result = self.loop.run_until_complete(cli.ask_user_handler(tc))
    self.assertTrue(result)

  @mock.patch("builtins.input")
  def test_ask_user_handler_deny(self, mock_input):
    """Verifies that the handler returns False when the user declines."""
    mock_input.return_value = "n"
    tc = types.ToolCall(name="test_tool", args={})
    result = self.loop.run_until_complete(cli.ask_user_handler(tc))
    self.assertFalse(result)

  @mock.patch("builtins.input")
  def test_ask_user_handler_eof(self, mock_input):
    """Verifies that the handler returns False on EOFError."""
    mock_input.side_effect = EOFError
    tc = types.ToolCall(name="test_tool", args={})
    result = self.loop.run_until_complete(cli.ask_user_handler(tc))
    self.assertFalse(result)


if __name__ == "__main__":
  unittest.main()
