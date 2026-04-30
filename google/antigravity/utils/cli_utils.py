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

"""CLI utilities for rendering agent steps and handling interactions."""

import sys
import threading
import time

from prompt_toolkit.utils import get_cwidth
from rich import box
from rich.console import Console
from rich.markdown import Heading
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text as RichText


# ANSI color codes
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"
_ORANGE = "\033[38;5;208m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_MAGENTA = "\033[35m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"

_MODEL_INDICATOR = f"⏺{_RESET}"

_SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
_SPINNER_COLORS = [_CYAN, _MAGENTA, _YELLOW, _GREEN, _BLUE]

INPUT_PROMPT = f"\n{_CYAN}{_BOLD}→{_RESET} "
STOPPED_PROMPT = f"\n{_DIM}⏹ Stopped{_RESET}"
GOODBYE_MSG = f"\n{_DIM}Goodbye! 👋{_RESET}"

_MARKDOWN_ENABLED: bool = False


def set_markdown_enabled(enabled: bool) -> None:
  """Enable or disable markdown rendering for agent responses."""
  global _MARKDOWN_ENABLED
  _MARKDOWN_ENABLED = enabled


class _LeftAlignedHeading(Heading):  # pytype: disable=invalid-function-definition
  """Heading that renders left-aligned instead of centered."""

  def __rich_console__(self, console, options):  # pytype: disable=signature-mismatch
    self.text.justify = "left"  # pytype: disable=attribute-error
    if self.tag == "h1":  # pytype: disable=attribute-error
      yield Panel(self.text, box=box.HEAVY, style="markdown.h1.border")  # pytype: disable=attribute-error
    else:
      if self.tag == "h2":  # pytype: disable=attribute-error
        yield RichText("")
      yield self.text  # pytype: disable=attribute-error


class _LeftAlignedMarkdown(Markdown):
  """Markdown renderer with left-aligned headings."""

  elements = {**Markdown.elements, "heading_open": _LeftAlignedHeading}


_MARKDOWN_CONSOLE = Console(force_terminal=True, highlight=False)


def _render_markdown(text: str) -> str:
  """Renders markdown text to a string with ANSI formatting."""
  if not _MARKDOWN_ENABLED:
    return text

  with _MARKDOWN_CONSOLE.capture() as capture:
    _MARKDOWN_CONSOLE.print(_LeftAlignedMarkdown(text))
  return capture.get().rstrip()


class Spinner:
  """Animated spinner for loading states."""

  def __init__(self, message: str = "Thinking"):
    self._message = message
    self._running = False
    self._thread: threading.Thread | None = None
    self._frame_idx = 0
    self._color_idx = 0

  def start(self) -> None:
    self._running = True
    self._thread = threading.Thread(target=self._animate, daemon=True)
    self._thread.start()

  def stop(self) -> None:
    self._running = False
    if self._thread:
      self._thread.join(timeout=0.5)
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()

  def _animate(self) -> None:
    while self._running:
      frame = _SPINNER_FRAMES[self._frame_idx % len(_SPINNER_FRAMES)]
      color = _SPINNER_COLORS[self._color_idx % len(_SPINNER_COLORS)]
      sys.stdout.write(
          f"\r{color}{frame}{_RESET} {_DIM}{self._message}...{_RESET}"
      )
      sys.stdout.flush()
      self._frame_idx += 1
      if self._frame_idx % 4 == 0:
        self._color_idx += 1
      time.sleep(0.08)


def _display_width(s: str) -> int:
  """Returns the display width of a string, accounting for wide characters."""
  return get_cwidth(s)


def _center_display(s: str, width: int) -> str:
  """Centers a string based on display width, not character count."""
  display_w = _display_width(s)
  if display_w >= width:
    return s
  padding = width - display_w
  left_pad = padding // 2
  right_pad = padding - left_pad
  return " " * left_pad + s + " " * right_pad


def print_cli_header(
    title: str,
    extra_lines: dict[str, str] | None = None,
) -> None:
  """Prints a styled CLI header banner."""
  subtitle = "Type your message and press Enter • Ctrl+C to exit"
  inner_width = max(_display_width(title), _display_width(subtitle)) + 6
  bar = "─" * inner_width
  print(f"{_DIM}╭{bar}╮")
  print(f"│{' ' * inner_width}│")
  print(f"│{_RESET}{_BOLD}{_center_display(title, inner_width)}{_RESET}{_DIM}│")
  print(f"│{' ' * inner_width}│")
  print(f"├{bar}┤")
  print(f"│{_center_display(subtitle, inner_width)}│")
  print(f"╰{bar}╯{_RESET}")
  if extra_lines:
    for label, value in extra_lines.items():
      print(f"{_DIM}{label}: {value}{_RESET}")
  print()
