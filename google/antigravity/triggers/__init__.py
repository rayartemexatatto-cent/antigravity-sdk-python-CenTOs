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

"""Trigger system for the Antigravity SDK.

Triggers are long-lived async functions that run alongside an agent
session, react to external events (cron, file changes, webhooks),
and push messages back into the agent.

Public API:
  TriggerContext — handle for sending messages to the agent.
  Trigger — type alias for async trigger functions.
  TriggerRunner — lifecycle manager for triggers.
  every — helper for interval/cron triggers.
  on_file_change — helper for file-watching triggers.
  TriggerDelivery — controls message delivery (re-exported from types).
  FileChange — a single filesystem change (re-exported from types).
  FileChangeKind — kind of filesystem change (re-exported from types).
"""

from google.antigravity.triggers.helpers import every
from google.antigravity.triggers.helpers import on_file_change
from google.antigravity.triggers.trigger_runner import TriggerRunner
from google.antigravity.triggers.triggers import Trigger
from google.antigravity.triggers.triggers import TriggerContext
from google.antigravity.types import FileChange
from google.antigravity.types import FileChangeKind
from google.antigravity.types import TriggerDelivery
