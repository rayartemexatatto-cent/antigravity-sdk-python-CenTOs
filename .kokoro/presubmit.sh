#!/bin/bash
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

# Kokoro presubmit script for antigravity-sdk-py.
# Runs unit tests and linting on every GoB change.

set -eo pipefail

cd "${KOKORO_ARTIFACTS_DIR}/git/antigravity-sdk-py"

echo "--- Setting up Python environment ---"
# The ubuntu2004 Docker image ships Python 3.8; install 3.13.
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq software-properties-common > /dev/null 2>&1
add-apt-repository -y ppa:deadsnakes/ppa > /dev/null 2>&1
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq python3.13 python3.13-venv python3.13-dev > /dev/null 2>&1

python3.13 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel

echo "--- Installing package and test dependencies ---"
pip install -e ".[dev]"

echo "--- Running tests ---"
python -m pytest -v --tb=short

echo "--- Running lint ---"
python -m ruff check google/

echo "--- Presubmit passed ---"
