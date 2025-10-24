"""Textual-based sandbox UI for experimenting with the chat orchestrator."""

from __future__ import annotations

import traceback
from typing import Any, Dict, Optional

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Checkbox, Footer, Header, Input, RichLog, Static

from ..conversation import chat_once
from ..environment import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    load_local_env,
    resolve_project_paths,
)
from ..tool_registry import ToolRegistry
from ..transcript import Transcript


SYSTEM_PROMPT = (
    "You are a finance assistant. Provide concise market context and only call tools when the user"
    " explicitly asks for specific data points."
)


class SimpleTextualApp(App):
    """Minimal Textual application rendering chat, tool output, and diagnostics panes."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #body {
        layout: vertical;
        padding: 1 2;
    }

    #controls {
        layout: vertical;
        padding: 0;
        margin-bottom: 1;
    }

    #prompt_row {
        layout: horizontal;
        padding: 0;
    }

    #options_row {
        layout: horizontal;
        padding: 0;
    }

    #stream_status {
        height: auto;
        color: $secondary;
    }

    #panes {
        layout: horizontal;
        height: 1fr;
    }

    .pane {
        layout: vertical;
        border: tall $surface-lighten-1;
        padding: 1;
        width: 1fr;
    }

    .pane_title {
        text-align: center;
        margin-bottom: 1;
        color: $text-muted;
    }

    .log { height: 1fr; }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        paths = resolve_project_paths()
        load_local_env(paths.env_file)
        self.registry = ToolRegistry(paths.tools_root)
        self.registry.load()
        self.transcript = Transcript(system_prompt=SYSTEM_PROMPT)
        self.base_url = DEFAULT_BASE_URL
        self.model = DEFAULT_MODEL
        self.timeout = 60.0

        self._stream_buffer = ""

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="body"):
            with Vertical(id="controls"):
                with Horizontal(id="prompt_row"):
                    yield Input(placeholder="Enter prompt…", id="prompt", classes="control")
                    yield Button("Send", id="send")
                with Horizontal(id="options_row"):
                    yield Checkbox("Stream tokens", value=True, id="stream")
                    yield Checkbox("Trace timings", value=True, id="trace")
                yield Static("", id="stream_status")
            with Horizontal(id="panes"):
                with Vertical(id="conversation_pane", classes="pane"):
                    yield Static("Conversation", classes="pane_title")
                    yield RichLog(id="conversation_log", wrap=True, highlight=False, markup=False, classes="log")
                with Vertical(id="tools_pane", classes="pane"):
                    yield Static("Tool Output", classes="pane_title")
                    yield RichLog(id="tools_log", wrap=True, highlight=False, markup=False, classes="log")
                with Vertical(id="diagnostics_pane", classes="pane"):
                    yield Static("Diagnostics", classes="pane_title")
                    yield RichLog(id="diagnostics_log", wrap=True, highlight=False, markup=False, classes="log")
        yield Footer()

    async def on_mount(self) -> None:
        self.prompt_input = self.query_one("#prompt", Input)
        self.send_button = self.query_one("#send", Button)
        self.stream_checkbox = self.query_one("#stream", Checkbox)
        self.trace_checkbox = self.query_one("#trace", Checkbox)
        self.conversation_log = self.query_one("#conversation_log", RichLog)
        self.tools_log = self.query_one("#tools_log", RichLog)
        self.diagnostics_log = self.query_one("#diagnostics_log", RichLog)
        self.stream_status = self.query_one("#stream_status", Static)

        self.set_focus(self.prompt_input)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send":
            await self._handle_send()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "prompt":
            await self._handle_send()

    async def _handle_send(self) -> None:
        prompt = self.prompt_input.value.strip()
        if not prompt:
            return
        if getattr(self, "_chat_inflight", False):
            return

        self._chat_inflight = True
        self.prompt_input.value = ""
        self.prompt_input.disabled = True
        self.send_button.disabled = True
        self._stream_buffer = ""
        self.stream_status.update("")

        self.conversation_log.write(f"You: {prompt}")

        stream = bool(self.stream_checkbox.value)
        trace = bool(self.trace_checkbox.value)

        # Manage transcript for this turn.
        self.transcript.add_user(prompt)

        self._worker = self._run_chat(prompt, stream, trace)

    @work(thread=True, exclusive=True)
    def _run_chat(self, prompt: str, stream: bool, trace: bool) -> None:
        def handle_stream(delta: str) -> None:
            if not delta:
                return
            self.call_from_thread(self._update_stream, delta)

        def handle_tool(payload: Dict[str, Any]) -> None:
            self.call_from_thread(self._append_tool_result, payload)

        try:
            content, recorder, _ = chat_once(
                self.transcript,
                self.registry,
                self.base_url,
                self.model,
                self.timeout,
                verbose=False,
                trace=trace,
                live_stream=stream,
                stream_consumer=handle_stream if stream else None,
                tool_result_handler=handle_tool,
            )
            self.call_from_thread(self._finalise_response, content)
            if trace and recorder:
                report = recorder.report(width=60)
                self.call_from_thread(self._update_diagnostics, report)
            else:
                self.call_from_thread(
                    self._update_diagnostics,
                    "Tracing disabled for this turn.",
                )
        except Exception as exc:
            self.transcript.pop_last()
            message = f"{exc}\n{traceback.format_exc(limit=1)}"
            self.call_from_thread(self._handle_error, message)
        finally:
            self.call_from_thread(self._finish_turn)

    def _update_stream(self, delta: str) -> None:
        self._stream_buffer += delta
        self.stream_status.update(f"Assistant (streaming): {self._stream_buffer}")

    def _finalise_response(self, content: str) -> None:
        if not content:
            content = "[no content]"
        self.conversation_log.write(f"Assistant: {content}")
        self.stream_status.update("")
        self._stream_buffer = ""

    def _append_tool_result(self, payload: Dict[str, Any]) -> None:
        name = payload.get("name", "unknown")
        call_id = payload.get("call_id")
        arguments = payload.get("arguments")
        result = payload.get("result")
        header = f"[tool:{name}]"
        if call_id:
            header += f" ({call_id})"
        self.tools_log.write(f"{header}\n  arguments: {arguments}\n  result: {result}\n")

    def _update_diagnostics(self, text: str) -> None:
        self.diagnostics_log.clear()
        self.diagnostics_log.write(text or "No diagnostics available.")

    def _handle_error(self, message: str) -> None:
        self.diagnostics_log.write(f"[error] {message}")
        self.bell()

    def _finish_turn(self) -> None:
        self.prompt_input.disabled = False
        self.send_button.disabled = False
        self._chat_inflight = False
        self.set_focus(self.prompt_input)


def main() -> None:
    app = SimpleTextualApp()
    app.run()


if __name__ == "__main__":
    main()
