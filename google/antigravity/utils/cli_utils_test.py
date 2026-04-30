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

import unittest
from unittest import mock

from google.antigravity.utils import cli_utils


class CliUtilsTest(unittest.TestCase):
  """Validates CLI utilities in cli_utils.py."""

  @mock.patch("sys.stdout.write")
  @mock.patch("sys.stdout.flush")
  def test_spinner(self, mock_flush, mock_write):
    """Verifies spinner animation starts and stops."""
    spinner = cli_utils.Spinner("Loading")
    spinner.start()
    self.assertTrue(spinner._running)
    self.assertTrue(spinner._thread.is_alive())
    spinner.stop()
    self.assertFalse(spinner._running)
    # Check that it cleared the line
    mock_write.assert_any_call("\r\033[K")
    mock_flush.assert_called()


if __name__ == "__main__":
  unittest.main()
