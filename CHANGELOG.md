# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.4.0] — 2026-11-19

### Changed
- The Qwen `code_interpreter` phase is now **fully excluded** from Markdown
  (both the source code and the execution output).

## [0.3.0] — 2026-11-18

### Added
- **Qwen** export support (`chat.history.messages`, `parentId` tree).
- Network selection combo box: Auto / DeepSeek / Qwen.
- Automatic format detection based on the JSON structure.

### Fixed
- `'list' object has no attribute 'get'` when parsing Qwen exports
  whose root is a list.

## [0.2.0] — 2026-11-17

### Fixed
- Correct handling of DeepSeek service fragments (`TOOL_SEARCH`, `READ_LINK`).
- Restored corrupted string literals (`\n`, f-strings).

## [0.1.0] — 2026-11-17

### Added
- Initial release: Multithreaded conversion,
  operation log, result opening.
