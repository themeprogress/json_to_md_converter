# JSON - Markdown Converter

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Qt](https://img.shields.io/badge/Qt-PySide6-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

A desktop application that converts **DeepSeek** and **Qwen** chat exports
from JSON into clean, readable Markdown files.

## Features

- **PySide6 (Qt) GUI** — modern Fusion-styled interface
- **Automatic format detection** based on the JSON structure
- **Two networks supported**: DeepSeek and Qwen (plus manual override)
- **Multithreaded conversion** — runs in a `QThread`, the UI never freezes
- **Smart filtering of service data** — interpreter code and its output
  never leak into the resulting document
- **Optional service blocks**: model reasoning (`thinking_summary`),
  search queries and read links
- **Per-message timestamps** preserved
- **Cross-platform result opening** (Notepad / TextEdit / xdg-open)
- **UTF-8** — full Unicode support

## Supported Formats

| Network  | Export structure                        | Extracted into Markdown                                      |
| -------- | --------------------------------------- | ------------------------------------------------------------ |
| DeepSeek | `messages[] → fragments[]`              | `REQUEST`, `RESPONSE`; optionally `TOOL_SEARCH`, `READ_LINK` |
| Qwen     | `data[].chat.history.messages{}` (tree) | `answer` phases; optionally `thinking_summary`               |

> The `code_interpreter` phase (source code **and** execution output)
> is intentionally excluded from the output for both formats.

See [docs/FORMATS.md](docs/FORMATS.md) for a detailed format specification.

## Installation

### Requirements

- Python **3.9+**
- PySide6

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/USERNAME/chat-json-to-md.git
cd chat-json-to-md

# 2. (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

## Running

```bash
python export.py
```

## Usage

1. **Select the source format**: `Auto`, `DeepSeek` or `Qwen`.
   - `Auto` detects the format from the JSON structure automatically.
2. Click **Browse...** and pick an exported JSON file.
   The output `.md` path is filled in automatically
   (you can change it with **Save As...**).
3. Optionally tick **"Include service fragments (tools, reasoning)"**:

   | Network  | What the checkbox adds                           |
   | -------- | ------------------------------------------------ |
   | DeepSeek | `Tool` blocks with search queries and read links |
   | Qwen     | `Reasoning` blocks (`thinking_summary`)          |

4. Click **Convert**.
5. Watch the progress in the **Operation Log**; when finished,
   click **Open File** to view the result.

## Project Structure

```
json_to_md_converter/
├── export.py          # The whole app: parsers + GUI + conversion thread
├── requirements.txt   # PySide6
├── docs/
│   └── FORMATS.md     # Specification of the supported JSON formats
└── ...
```

## How It Works

### DeepSeek

The parser walks the `messages[]` array; each message contains a
`fragments[]` array. `REQUEST` fragments become user messages, `RESPONSE`
fragments become assistant messages. Service fragments (`TOOL_SEARCH` /
`READ_LINK`) are added only when the option is enabled.

### Qwen

Messages are stored in a dictionary keyed by UUID and linked via
`parentId` / `childrenIds`. The parser rebuilds the chronological chain
starting from the root message, then processes each node's `content_list`:
the `answer` phase goes into the main text, `thinking_summary` is optional,
and `code_interpreter` is always skipped.

## Troubleshooting

| Problem                                | Solution                                                           |
| -------------------------------------- | ------------------------------------------------------------------ |
| "Could not detect the format"          | Select the network manually in the combo box                       |
| `'list' object has no attribute 'get'` | Outdated parser: the Qwen export root is a list. Update to v0.3.0+ |
| Code blocks appear in the Markdown     | Interpreter code has been excluded since v0.4.0 — update           |
| "No messages found"                    | Make sure the file is a full chat export, not a fragment           |

## Roadmap

- [ ] CLI mode without the GUI
- [ ] ChatGPT, Gemini, Grok export support
- [ ] HTML / DOCX export
- [ ] Packaging into standalone executables (PyInstaller)

## Contributing

Bug reports, ideas and pull requests are welcome!
See [CONTRIBUTING.md](CONTRIBUTING.md) and the [issue templates](.github/ISSUE_TEMPLATE).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

This project is licensed under the [MIT License](LICENSE).
