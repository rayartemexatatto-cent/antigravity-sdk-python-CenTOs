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
# Runs unit tests on every GoB change.

set -eo pipefail

cd "${KOKORO_ARTIFACTS_DIR}/git/antigravity-sdk-py"
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# --- Python 3.13 via pyenv (pre-installed on the Kokoro image) ---
echo "--- Setting up Python 3.13 ---"
eval "$(pyenv init -)"
pyenv install -s 3.13
pyenv global 3.13
python3 --version

echo "--- Installing build tools with hash verification ---"
# Install build/release tools with hash verification.
# See go/pip-install-remediation.
python3 -m pip install \
  --require-hashes \
  --no-deps \
  -r "${SCRIPT_DIR}/requirements-build.txt"

echo "--- Installing package and test dependencies ---"
# Install the package under test and its dev dependencies.
# This is the package being built, not a supply-chain dependency,
# so hash verification is not applicable here.
python3 -m pip install -e ".[dev]"

echo "--- Running tests ---"
python3 -m pytest -v --tb=short

echo "--- Building wheel ---"
python3 -m build --wheel --outdir dist/

echo "--- Verifying wheel installs and imports correctly ---"
python3 -m pip install --force-reinstall --no-deps dist/*.whl
python3 -c "from google.antigravity.agent import Agent; print('Import OK: Agent')"
python3 -c "from google.antigravity.connections.local_connection import LocalConnection; print('Import OK: LocalConnection')"

echo "--- Presubmit passed ---"
