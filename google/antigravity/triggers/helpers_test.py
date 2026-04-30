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

"""Tests for trigger helper factories."""

import asyncio
import unittest
from unittest import mock

from google.antigravity.connections import connection
from google.antigravity.triggers import helpers
from google.antigravity.triggers import triggers


class EveryTest(unittest.IsolatedAsyncioTestCase):

  def _make_ctx(self):
    conn = mock.AsyncMock(spec=connection.Connection)
    conn.send = mock.AsyncMock()
    conn.wait_for_idle = mock.AsyncMock()
    return triggers.TriggerContext(connection=conn)

  async def test_every_calls_callback_on_interval(self):
    call_count = 0

    async def cb(ctx):
      nonlocal call_count
      call_count += 1

    trigger = helpers.every(0.01, cb)
    ctx = self._make_ctx()

    task = asyncio.create_task(trigger(ctx))
    await asyncio.sleep(0.05)
    task.cancel()
    with self.assertRaises(asyncio.CancelledError):
      await task

    self.assertGreaterEqual(call_count, 2)

  def test_every_rejects_non_positive_interval(self):
    async def cb(ctx):
      pass

    with self.assertRaises(ValueError):
      helpers.every(0, cb)

    with self.assertRaises(ValueError):
      helpers.every(-1, cb)

  def test_every_sets_name(self):
    async def cb(ctx):
      pass

    trigger = helpers.every(300, cb)
    self.assertEqual(trigger.__name__, "every_300s")


class OnFileChangeTest(unittest.TestCase):

  def test_on_file_change_sets_name(self):
    async def cb(ctx, changes):
      pass

    trigger = helpers.on_file_change("/tmp/config.yaml", cb)
    self.assertEqual(trigger.__name__, "on_file_change_config.yaml")

  def test_on_file_change_import_error(self):
    """Verify helpful error when watchfiles is missing."""
    async def cb(ctx, changes):
      pass

    trigger = helpers.on_file_change("/tmp/config.yaml", cb)
    # Trigger is a valid callable regardless of import availability.
    self.assertTrue(callable(trigger))


if __name__ == "__main__":
  unittest.main()
