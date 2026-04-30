# Antigravity SDK Triggers

Triggers are long-lived async functions that run alongside an agent session.
They react to external events (cron schedules, file changes, webhooks) and
push messages back into the agent.

## Overview

Triggers complement **hooks** — they handle different concerns:

| Concept | Hooks | Triggers |
|---------|-------|----------|
| Lifetime | Single dispatch point | Entire session |
| Execution | Inline, blocking | Background, async |
| Purpose | React to agent lifecycle | React to external events |
| Control flow | Can block/modify execution | Can only send messages |

Use **hooks** for agent lifecycle events (pre_turn, post_tool_call, etc.).
Use **triggers** for external events (timers, file changes, webhooks).

## Quick Start

```python
from google.antigravity.triggers import (
    TriggerContext, TriggerDelivery, every, on_file_change,
    TriggerRunner, FileChange, FileChangeKind,
)

# 1. Define a trigger (it's just an async function).
async def health_check(ctx: TriggerContext) -> None:
  """Pings the agent every 5 minutes."""
  while True:
    await asyncio.sleep(300)
    await ctx.send("Health check", delivery=TriggerDelivery.WAIT_IDLE)

# 2. Or use a helper factory.
async def on_config_change(ctx, changes: list[FileChange]):
  for change in changes:
    await ctx.send(f"{change.kind.value}: {change.path}")

config_watcher = on_file_change("/etc/app/config.yaml", on_config_change)

# 3. Wire them into the session.
async with TriggerRunner(
    triggers=[health_check, config_watcher],
    connection=connection,
) as runner:
    # ... agent session ...
    pass
# stop() called automatically on exit.
```

## Core Concepts

### TriggerContext

The handle provided to every trigger at startup. Provides:

-   **`send(content, delivery=TriggerDelivery.SEND_IMMEDIATELY)`**: Push a message to the
    agent.

### Delivery Modes

Controls how trigger messages are delivered to the agent:

| Mode | Behavior |
|------|----------|
| `SEND_IMMEDIATELY` | Send immediately (non-blocking). Default. |
| `WAIT_IDLE` | Wait until agent is idle, then send. |

> **TODO**: `INTERRUPT` mode (cancel current turn, then send) is planned but
> deferred due to safety implications for in-flight tool calls.

### Trigger Type

A `Trigger` is any `async def` that accepts a `TriggerContext`:

```python
async def my_trigger(ctx: TriggerContext) -> None:
  ...
```

No base class, no registration ceremony — just a function.

## Helper Factories

### `every(interval_seconds, callback)`

Creates a trigger that runs a callback on a fixed interval.

```python
async def check_status(ctx: TriggerContext) -> None:
  status = await check_service()
  if not status.ok:
    await ctx.send(f"Unhealthy: {status}", delivery=TriggerDelivery.WAIT_IDLE)

my_trigger = every(300, check_status)  # Every 5 minutes.
```

### `on_file_change(path, callback)`

Creates a trigger that reacts to filesystem changes. Uses `watchfiles` for
efficient OS-level watching (lazy import — only needed if you use this helper).

The callback receives a `list[FileChange]` where each `FileChange` has:

-   **`kind`**: A `FileChangeKind` enum (`ADDED`, `MODIFIED`, `DELETED`).
-   **`path`**: Absolute path to the changed file.

```python
async def handle_change(ctx, changes: list[FileChange]):
  for change in changes:
    if change.kind == FileChangeKind.MODIFIED:
      await ctx.send(f"Updated: {change.path}")

my_trigger = on_file_change("/path/to/watched/dir", handle_change)
```

## TriggerRunner

Manages the lifecycle of registered triggers:

-   **`start()`**: Creates an asyncio task per trigger. Called at session start.
-   **`stop()`**: Cancels all tasks and waits for cleanup. Called at session end.
-   **`async with`**: Supports use as an async context manager for automatic cleanup.
-   **Isolation**: Unhandled exceptions in a trigger are logged but don't crash
    the session or affect other triggers. No auto-restart.
-   **No ordering**: Triggers run as independent tasks with no ordering
    guarantees.

Developers are responsible for everything between start and stop — their own
event loops, cleanup, and side effects.

> **Note**: The TriggerRunner assumes a 1:1 relationship between the
> connection and the agent session. Sharing a single connection across
> multiple agents is not supported.

## Architecture

```
+-------------------------------------------+
|                Session                     |
|                                           |
|  +----------+                             |
|  |HookRunner|  (agent lifecycle hooks)    |
|  +----------+                             |
|       |                                   |
|  dispatch_*()                             |
|       |                                   |
|       v                  +----------+     |
|  [Agent Loop]            | Triggers |     |
|       ^                  +----+-----+     |
|       |                      |            |
|       |                 ctx.send()        |
|       |                      |            |
|  +----+------+          +----v-----+      |
|  |Connection |<---------|  Runner  |      |
|  +-----------+          +----------+      |
+-------------------------------------------+
```

Hooks and triggers are independent — hooks handle agent lifecycle, triggers
handle external events. Both communicate with the agent through the
Connection.

## Files

| File | Role |
|------|------|
| `triggers.py` | `TriggerContext`, `Trigger` type alias |
| `trigger_runner.py` | `TriggerRunner` lifecycle management |
| `helpers.py` | `every()`, `on_file_change()` factories |
| `__init__.py` | Package re-exports |

## Tests

```bash
bazel test //triggers:all
```
