# Hooks TODO

## Policy System

- **Prefix/regex tool matching**: Extend `_matches_tool` in `policy.py` to
  support prefix patterns (e.g., `file::*` to match all file-related tools) and
  compiled regex objects. The matching logic is isolated in a single helper,
  making this a low-risk extension.
