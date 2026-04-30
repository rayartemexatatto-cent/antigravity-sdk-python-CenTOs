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

"""Tests for TriggerContext and delivery modes."""

import unittest
from unittest import mock

from google.antigravity import types
from google.antigravity.connections import connection
from google.antigravity.triggers import triggers


class TriggerContextTest(unittest.IsolatedAsyncioTestCase):

  def _make_mock_connection(self):
    conn = mock.AsyncMock(spec=connection.Connection)
    conn.send_trigger_notification = mock.AsyncMock()
    return conn

  async def test_send_calls_connection_send_trigger_notification(self):
    conn = self._make_mock_connection()
    ctx = triggers.TriggerContext(connection=conn)

    await ctx.send("hello")

    conn.send_trigger_notification.assert_called_once_with("hello")


class TriggerTypeTest(unittest.TestCase):

  def test_trigger_is_callable_type(self):
    """Verify that an async def is a valid Trigger."""

    async def my_trigger(ctx: triggers.TriggerContext) -> None:
      pass

    # Type check: should be assignable to Trigger.
    trigger: triggers.Trigger = my_trigger
    self.assertTrue(callable(trigger))


if __name__ == "__main__":
  unittest.main()
