"""
ai_worker.py — Thread-safe background AI worker for NeuroVault Pro.

Communicates with a local LLM via the OpenAI-compatible API (e.g. LM Studio).
All requests are queued and processed in a dedicated background thread so the
UI thread is never blocked.  Results are dispatched back to the caller through
a callback mechanism that safely schedules work on the main Tkinter thread.

Settings are read dynamically from an optional SettingsManager, so changes
made in the UI take effect immediately — no restart needed.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

import requests

if TYPE_CHECKING:
    from settings import SettingsManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_LLM_ENDPOINT = "http://127.0.0.1:1234/v1"
REQUEST_TIMEOUT = 180          # seconds — local LLMs can be slow


class TaskType(str, Enum):
    """Kinds of work the background worker can perform."""
    SUMMARIZE = "summarize"      # Generate a summary for a snippet
    AUTO_TAG = "auto_tag"        # Suggest tags for a snippet
    CHAT = "chat"                # RAG-powered conversational query


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AiTask:
    """A unit of work pushed onto the worker queue."""
    task_type: TaskType
    prompt: str
    callback: Callable[[str, Optional[str]], None]  # (result_str, error_str)
    extra: dict = field(default_factory=dict)        # arbitrary context


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

SUMMARIZE_PROMPT = (
    "You are a code analyst.  Given the following snippet, produce a concise "
    "one-paragraph summary (max 80 words).  Return ONLY the summary text — "
    "no preamble, no markdown formatting.\n\n"
    "{content}"
)

TAG_PROMPT = (
    "You are a code analyst.  Given the following snippet, suggest up to five "
    "relevant tags in lowercase, hyphen-separated form (e.g. 'python-async').\n"
    "Return ONLY the tags separated by commas — no preamble.\n\n"
    "{content}"
)

CHAT_SYSTEM_PROMPT = (
    "You are NeuroVault Pro's AI assistant.  You answer questions about the "
    "user's saved code snippets and notes.  Use the provided context from their "
    "knowledge base to give accurate, helpful answers.  If you don't know, say so."
)


# ---------------------------------------------------------------------------
# LLM client — thin wrapper around requests
# ---------------------------------------------------------------------------

class LlmClient:
    """Stateless HTTP client for an OpenAI-compatible local LLM."""

    def __init__(self, endpoint: str = DEFAULT_LLM_ENDPOINT):
        self.endpoint = endpoint.rstrip("/")

    # -- public helpers -----------------------------------------------------

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout: int = REQUEST_TIMEOUT,
    ) -> str:
        """Send a chat-completions request and return the assistant reply."""
        payload: dict[str, Any] = {
            "model": "local-model",          # LM Studio ignores this
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        resp = requests.post(
            f"{self.endpoint}/chat/completions",
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    def ping(self) -> bool:
        """Return ``True`` if the LLM endpoint appears reachable."""
        try:
            requests.get(f"{self.endpoint}/models", timeout=5)
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Background worker — single consumer thread + queue
# ---------------------------------------------------------------------------

class AiWorker:
    """Single-threaded background worker that processes AI tasks from a queue.

    The UI creates an ``AiWorker`` instance and calls its public enqueue
    methods (``summarize``, ``auto_tag``, ``chat``).  Each call pushes an
    ``AiTask`` onto an internal :class:`queue.Queue`.  A dedicated daemon
    thread drains the queue, talks to the LLM, and invokes the caller's
    callback — which must schedule UI updates via ``.after()`` on the main
    Tkinter root.

    Settings (endpoint, temperature, max_tokens) are read from an optional
    :class:`SettingsManager` at request time so changes in the UI take effect
    immediately without restarting the app.

    Example::

        worker = AiWorker(settings_manager)
        worker.summarize(snippet_content, lambda text, err: ...)
    """

    def __init__(self, settings_manager: "SettingsManager | None" = None):
        self._queue: queue.Queue[AiTask] = queue.Queue()
        self._settings_mgr = settings_manager
        self._client_lock = threading.Lock()
        self._client = LlmClient(self._get_endpoint())
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="AiWorker"
        )
        self._running = False

    # -- dynamic settings access --------------------------------------------

    def _get_endpoint(self) -> str:
        if self._settings_mgr is not None:
            return self._settings_mgr.get_endpoint()
        return DEFAULT_LLM_ENDPOINT

    def _get_temperature(self) -> float:
        if self._settings_mgr is not None:
            return self._settings_mgr.get_temperature()
        return 0.3

    def _get_max_tokens(self) -> int:
        if self._settings_mgr is not None:
            return self._settings_mgr.get_max_tokens()
        return 1024

    def _get_timeout(self) -> int:
        if self._settings_mgr is not None:
            return self._settings_mgr.get_request_timeout()
        return REQUEST_TIMEOUT

    def _recreate_client(self) -> None:
        """Rebuild the HTTP client with the current endpoint."""
        new_client = LlmClient(self._get_endpoint())
        with self._client_lock:
            self._client = new_client

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Start the background processing thread."""
        if not self._running:
            self._running = True
            self._thread.start()

    def stop(self) -> None:
        """Signal the worker to shut down after finishing pending tasks."""
        self._running = False
        # Wake the thread in case it's blocked on get_nowait
        self._queue.put(AiTask(
            task_type=TaskType.CHAT, prompt="", callback=lambda *_: None,
        ))

    def is_available(self) -> bool:
        """Check whether the LLM endpoint responds (reads current settings)."""
        self._recreate_client()
        return self._client.ping()

    # -- public enqueue helpers ---------------------------------------------

    def summarize(self, content: str, callback: Callable) -> None:
        """Queue a summarization request for *content*."""
        prompt = SUMMARIZE_PROMPT.format(content=content[:4000])  # cap length
        self._queue.put(AiTask(
            task_type=TaskType.SUMMARIZE, prompt=prompt, callback=callback,
        ))

    def auto_tag(self, content: str, callback: Callable) -> None:
        """Queue an auto-tagging request for *content*."""
        prompt = TAG_PROMPT.format(content=content[:4000])
        self._queue.put(AiTask(
            task_type=TaskType.AUTO_TAG, prompt=prompt, callback=callback,
        ))

    def chat(self, messages: list[dict], callback: Callable) -> None:
        """Queue a RAG-style chat request."""
        self._queue.put(AiTask(
            task_type=TaskType.CHAT,
            prompt=json.dumps(messages),  # serialise for the worker thread
            callback=callback,
        ))

    # -- internal loop ------------------------------------------------------

    def _run_loop(self) -> None:
        """Main loop — runs in a background daemon thread."""
        while self._running:
            try:
                task = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            result, error = self._process_task(task)
            # Invoke callback on the *caller's* thread context.
            # The caller is responsible for .after()-ing UI updates.
            try:
                task.callback(result, error)
            except Exception as exc:
                logger.error("Callback failed: %s", exc)

    def _process_task(self, task: AiTask) -> tuple[str, Optional[str]]:
        """Execute a single task and return (result, error)."""
        # Guard against empty prompts (e.g., stale tasks at shutdown)
        if not task.prompt or not task.prompt.strip():
            return "", "Empty prompt"

        # Always read current settings before each request
        self._recreate_client()
        temperature = self._get_temperature()
        max_tokens = self._get_max_tokens()
        timeout = self._get_timeout()

        try:
            if task.task_type == TaskType.SUMMARIZE:
                reply = self._client.chat(
                    [{"role": "user", "content": task.prompt}],
                    temperature=temperature, max_tokens=max_tokens, timeout=timeout,
                )
                return reply, None

            elif task.task_type == TaskType.AUTO_TAG:
                reply = self._client.chat(
                    [{"role": "user", "content": task.prompt}],
                    temperature=temperature, max_tokens=max_tokens, timeout=timeout,
                )
                # Parse comma-separated tags; strip whitespace & lowercase
                tags = [t.strip().lower() for t in reply.split(",") if t.strip()]
                return json.dumps(tags), None

            elif task.task_type == TaskType.CHAT:
                messages = json.loads(task.prompt)
                # Prepend system prompt if not present
                if messages and messages[0].get("role") != "system":
                    messages.insert(0, {"role": "system", "content": CHAT_SYSTEM_PROMPT})
                reply = self._client.chat(
                    messages, temperature=temperature, max_tokens=max_tokens, timeout=timeout,
                )
                return reply, None

            else:
                return "", f"Unknown task type: {task.task_type}"

        except requests.exceptions.ConnectionError:
            return "", (
                "LM Studio is not running.  Start it and ensure the endpoint "
                "is reachable at your configured URL"
            )
        except requests.exceptions.Timeout:
            return "", f"Request timed out ({timeout}s) — try increasing timeout in Settings."
        except requests.exceptions.HTTPError as exc:
            return "", f"HTTP error from LLM: {exc}"
        except Exception as exc:
            logger.exception("Unhandled worker error")
            return "", str(exc)
