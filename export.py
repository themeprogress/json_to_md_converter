#!/usr/bin/env python3
"""
Chat JSON to Markdown Converter (PySide6 GUI) v0.4.0
Converts DeepSeek and Qwen chat exports (JSON) into Markdown files.
"""

import sys
import json
import platform
import subprocess
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QFileDialog,
    QTextEdit,
    QCheckBox,
    QGroupBox,
    QMessageBox,
    QProgressBar,
    QComboBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont


# Utils
def format_iso_datetime(iso_str: str) -> str:
    """Convert an ISO-8601 date string to a human-readable format."""
    if not iso_str:
        return ""
    try:
        clean = iso_str.replace("Z", "").split(".")[0]
        return datetime.fromisoformat(clean).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso_str


def format_unix_timestamp(ts) -> str:
    """Convert a Unix timestamp (seconds or milliseconds) to a readable format."""
    if not ts:
        return ""
    try:
        ts_int = int(ts)
        if ts_int > 1e12:
            ts_int //= 1000
        return datetime.fromtimestamp(ts_int).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


# DeepSeek Parser
def parse_deepseek(data: dict, include_tools: bool = False) -> tuple:
    """Parse a DeepSeek JSON export."""
    title = data.get("title", "Untitled")
    metadata = {
        "chat_id": data.get("id", ""),
        "created": format_iso_datetime(data.get("inserted_at", "")),
        "updated": format_iso_datetime(data.get("updated_at", "")),
    }
    dialog = []

    for msg in data.get("messages", []):
        timestamp = format_iso_datetime(msg.get("inserted_at", ""))
        for frag in msg.get("fragments", []):
            ftype = frag.get("type", "")
            content = frag.get("content", "")

            if ftype == "REQUEST":
                dialog.append(
                    {"role": "User", "content": content, "timestamp": timestamp}
                )
            elif ftype == "RESPONSE":
                dialog.append(
                    {"role": "DeepSeek", "content": content, "timestamp": timestamp}
                )
            elif include_tools:
                if ftype == "TOOL_SEARCH":
                    queries = frag.get("queries", [])
                    results = frag.get("results", [])
                    tool_md = "**Search queries:**\n" + "\n".join(
                        [f"- `{q}`" for q in queries]
                    )
                    if results:
                        tool_md += f"\n\n**Found ({len(results)}):**\n" + "\n".join(
                            [
                                f"- [{r.get('title', '')}]({r.get('url', '')})"
                                for r in results[:5]
                            ]
                        )
                    dialog.append(
                        {"role": "Tool", "content": tool_md, "timestamp": timestamp}
                    )
                elif ftype == "READ_LINK":
                    results = frag.get("results", [])
                    tool_md = "**Read links:**\n" + "\n".join(
                        [
                            f"- [{r.get('title', '')}]({r.get('url', '')})"
                            for r in results
                        ]
                    )
                    dialog.append(
                        {"role": "Tool", "content": tool_md, "timestamp": timestamp}
                    )

    return title, metadata, dialog


# Qwen Parser
def parse_qwen(data, include_tools: bool = False) -> tuple:
    """Parse a Qwen JSON export."""
    # Normalize input (list or dict)
    chat_data = data[0] if isinstance(data, list) and data else data
    if isinstance(chat_data, dict) and "data" in chat_data:
        inner = chat_data["data"]
        chat_data = inner[0] if isinstance(inner, list) and inner else inner

    title = chat_data.get("title", "Untitled")
    metadata = {
        "chat_id": chat_data.get("id", ""),
        "created": format_unix_timestamp(chat_data.get("created_at")),
        "updated": format_unix_timestamp(chat_data.get("updated_at")),
    }

    messages_dict = chat_data.get("chat", {}).get("history", {}).get("messages", {})
    if not messages_dict:
        return title, metadata, []

    ordered = _build_qwen_chain(messages_dict)
    dialog = []

    for msg in ordered:
        role_raw = msg.get("role", "").lower()
        timestamp = format_unix_timestamp(msg.get("timestamp"))
        content_list = msg.get("content_list", [])

        # If content_list is empty, fall back to plain content
        if not content_list:
            c = msg.get("content", "")
            if c and c.strip():
                label = "User" if role_raw == "user" else "Qwen"
                dialog.append({"role": label, "content": c, "timestamp": timestamp})
            continue

        # Process phases inside content_list
        for phase_item in content_list:
            phase = phase_item.get("phase") or ""
            p_content = phase_item.get("content", "")
            p_role = (phase_item.get("role") or "").lower()

            if phase == "answer" and p_content.strip():
                label = "User" if p_role == "user" or role_raw == "user" else "Qwen"
                dialog.append(
                    {"role": label, "content": p_content, "timestamp": timestamp}
                )
            elif include_tools and phase == "thinking_summary":
                thoughts = (
                    (phase_item.get("extra") or {})
                    .get("summary_thought", {})
                    .get("content", [])
                )
                if thoughts:
                    dialog.append(
                        {
                            "role": "Reasoning",
                            "content": "\n\n".join(thoughts),
                            "timestamp": timestamp,
                        }
                    )

    return title, metadata, dialog


def _build_qwen_chain(messages_dict: dict) -> list:
    """Rebuild the chronological message chain from Qwen's tree structure."""
    root_id = next(
        (mid for mid, m in messages_dict.items() if m.get("parentId") is None),
        None,
    )
    if not root_id:
        return sorted(messages_dict.values(), key=lambda m: m.get("timestamp", 0))

    ordered, current, visited = [], root_id, set()
    while current and current in messages_dict and current not in visited:
        visited.add(current)
        msg = messages_dict[current]
        ordered.append(msg)
        children = msg.get("childrenIds") or []
        current = children[0] if children else None
    return ordered


# Common
def detect_format(data) -> str:
    """Detect the JSON format by its structure."""
    check = data[0] if isinstance(data, list) and data else data
    if isinstance(check, dict) and "data" in check:
        inner = check["data"]
        check = inner[0] if isinstance(inner, list) and inner else inner
    if not isinstance(check, dict):
        return "unknown"

    msgs = check.get("messages")
    if (
        isinstance(msgs, list)
        and msgs
        and isinstance(msgs[0], dict)
        and "fragments" in msgs[0]
    ):
        return "deepseek"

    hist = check.get("chat", {}).get("history", {}).get("messages")
    if isinstance(hist, dict) and hist:
        return "qwen"

    return "unknown"


def build_markdown(title, metadata, dialog, network):
    """Assemble a Markdown document from the extracted data."""
    lines = [f"# {title}", "", f"**Network:** {network}"]
    if metadata.get("chat_id"):
        lines.append(f"**Chat ID:** `{metadata['chat_id']}`")
    if metadata.get("created"):
        lines.append(f"**Created:** {metadata['created']}")
    if metadata.get("updated"):
        lines.append(f"**Updated:** {metadata['updated']}")
    lines.extend([f"**Total messages:** {len(dialog)}", "", "---", ""])

    for i, msg in enumerate(dialog, 1):
        header = f"### {i}. {msg['role']}"
        if msg["timestamp"]:
            header += f"  \n*{msg['timestamp']}*"
        lines.extend([header, "", msg["content"].strip(), "", "---", ""])

    return "\n".join(lines)


# Conversion worker
class ConvertWorker(QThread):
    """Background thread that performs the conversion without freezing the GUI."""

    log = Signal(str)
    error = Signal(str)
    done = Signal(str)

    def __init__(self, input_file, output_file, network, include_tools):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.network = network
        self.include_tools = include_tools

    def run(self):
        try:
            self.log.emit(f"Reading file: {self.input_file}")
            with open(self.input_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            network = self.network.lower()
            if network == "auto":
                detected = detect_format(data)
                if detected == "unknown":
                    self.error.emit(
                        "Could not detect the format. "
                        "Please select the network manually."
                    )
                    return
                self.log.emit(f"Auto-detected format: {detected.upper()}")
                network = detected

            self.log.emit("Parsing...")
            self.log.emit(
                f"Include service fragments: "
                f"{'Yes' if self.include_tools else 'No'}"
            )

            if network == "deepseek":
                title, meta, dialog = parse_deepseek(data, self.include_tools)
            elif network == "qwen":
                title, meta, dialog = parse_qwen(data, self.include_tools)
            else:
                self.error.emit(f"Unknown network: {network}")
                return

            self.log.emit(f"Extracted blocks: {len(dialog)}")
            if not dialog:
                self.error.emit("No messages found. Check the file or settings.")
                return

            self.log.emit("Building Markdown...")
            md = build_markdown(title, meta, dialog, network.capitalize())

            self.log.emit(f"Saving to: {self.output_file}")
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(md)

            self.log.emit("Conversion finished!")
            self.done.emit(self.output_file)

        except json.JSONDecodeError as e:
            self.error.emit(f"JSON parsing error: {e}")
        except Exception as e:
            self.error.emit(f"Error: {e}")


# Main Window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JSON to Markdown Converter v0.4.0")
        self.setMinimumSize(720, 620)
        self.worker = None
        self.output_file_path = None
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Format
        net_group = QGroupBox("Format")
        net_layout = QHBoxLayout(net_group)
        net_layout.addWidget(QLabel("Source:"))
        self.network_combo = QComboBox()
        self.network_combo.addItems(["Auto", "DeepSeek", "Qwen"])
        self.network_combo.setToolTip(
            "Auto — the format is detected from the JSON structure.\n"
            "DeepSeek — export with fragments[] (REQUEST/RESPONSE).\n"
            "Qwen — export with chat.history.messages (content_list)."
        )
        net_layout.addWidget(self.network_combo)
        net_layout.addStretch()
        layout.addWidget(net_group)

        # Input file
        in_group = QGroupBox("Input JSON File")
        in_layout = QHBoxLayout(in_group)
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("Select an exported JSON file...")
        self.input_path.setReadOnly(True)
        in_layout.addWidget(self.input_path)
        btn_in = QPushButton("Browse...")
        btn_in.setFixedWidth(120)
        btn_in.clicked.connect(self.browse_input)
        in_layout.addWidget(btn_in)
        layout.addWidget(in_group)

        # Output file
        out_group = QGroupBox("Output Markdown File")
        out_layout = QHBoxLayout(out_group)
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Will be created automatically...")
        out_layout.addWidget(self.output_path)
        btn_out = QPushButton("Save as...")
        btn_out.setFixedWidth(150)
        btn_out.clicked.connect(self.browse_output)
        out_layout.addWidget(btn_out)
        layout.addWidget(out_group)

        # Options
        opt_group = QGroupBox("Options")
        opt_layout = QVBoxLayout(opt_group)
        self.chk_tools = QCheckBox("Include service fragments (tools, reasoning)")
        self.chk_tools.setToolTip(
            "DeepSeek: TOOL_SEARCH, READ_LINK\n"
            "Qwen: thinking_summary\n"
            "(code and code_interpreter results are never included)"
        )
        opt_layout.addWidget(self.chk_tools)
        layout.addWidget(opt_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_convert = QPushButton("Convert")
        self.btn_convert.setFixedHeight(30)
        self.btn_convert.clicked.connect(self.start_conversion)
        btn_layout.addWidget(self.btn_convert)

        self.btn_open = QPushButton("Open File")
        self.btn_open.setFixedHeight(30)
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self.open_result)
        btn_layout.addWidget(self.btn_open)
        layout.addLayout(btn_layout)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Log
        log_group = QGroupBox("Operation Log")
        log_layout = QVBoxLayout(log_group)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 9))
        self.log_area.setMaximumHeight(150)
        log_layout.addWidget(self.log_area)
        layout.addWidget(log_group)

        self.statusBar().showMessage("Ready")

    def log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{ts}] {message}")

    def browse_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select JSON", "", "JSON (*.json);;All files (*)"
        )
        if path:
            self.input_path.setText(path)
            if not self.output_path.text():
                self.output_path.setText(str(Path(path).with_suffix(".md")))
            self.log(f"Selected file: {path}")

    def browse_output(self):
        default = (
            str(Path(self.input_path.text()).with_suffix(".md"))
            if self.input_path.text()
            else ""
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Save as", default, "Markdown (*.md);;All files (*)"
        )
        if path:
            self.output_path.setText(path)

    def start_conversion(self):
        inp = self.input_path.text()
        out = self.output_path.text()
        if not inp:
            QMessageBox.warning(self, "Error", "Please select a JSON file!")
            return
        if not Path(inp).exists():
            QMessageBox.warning(self, "Error", f"File not found:\n{inp}")
            return
        if not out:
            out = str(Path(inp).with_suffix(".md"))
            self.output_path.setText(out)

        self.btn_convert.setEnabled(False)
        self.btn_open.setEnabled(False)
        self.progress.setVisible(True)
        self.statusBar().showMessage("Converting...")

        self.worker = ConvertWorker(
            inp, out, self.network_combo.currentText(), self.chk_tools.isChecked()
        )
        self.worker.log.connect(self.log)
        self.worker.done.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_finished(self, output_file: str):
        self.progress.setVisible(False)
        self.btn_convert.setEnabled(True)
        self.btn_open.setEnabled(True)
        self.output_file_path = output_file
        self.statusBar().showMessage(f"Done: {output_file}")
        QMessageBox.information(self, "Done", f"Conversion finished!\n\n{output_file}")

    def on_error(self, error_msg: str):
        self.progress.setVisible(False)
        self.btn_convert.setEnabled(True)
        self.statusBar().showMessage("Error")
        self.log(error_msg)
        QMessageBox.critical(self, "Conversion Error", error_msg)

    def open_result(self):
        if not self.output_file_path:
            return
        system = platform.system()
        try:
            if system == "Windows":
                subprocess.Popen(["notepad.exe", self.output_file_path])
            elif system == "Darwin":
                subprocess.Popen(["open", self.output_file_path])
            else:
                subprocess.Popen(["xdg-open", self.output_file_path])
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
