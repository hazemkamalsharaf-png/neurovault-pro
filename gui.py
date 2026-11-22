"""
gui.py — CustomTkinter user interface for NeuroVault Pro.

Kaspersky-inspired modern dark UI with:
  • Deep navy background (#0a0e17) with subtle gradients
  • Glassmorphism cards with translucent surfaces
  • Vibrant cyan-to-blue gradient accents
  • Rounded corners everywhere (16–24px)
  • Clean sidebar navigation with pill-shaped active indicators
  • Smooth visual hierarchy and generous whitespace
  • Status badges with glowing dot indicators

Four main views:
  1. Dashboard / Editor   — create & save code snippets
  2. The Vault            — browse, search, and inspect saved snippets
  3. AI Chat (Local RAG)  — ask the local LLM about your knowledge base
  4. Settings             — configure LLM endpoint, temperature, timeouts…

All AI operations are offloaded to ``AiWorker`` so the UI never freezes.
"""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from ai_worker import AiWorker
    from db_manager import DbManager
    from settings import SettingsManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour palette — Kaspersky-inspired dark theme
# ---------------------------------------------------------------------------

BG_BASE      = "#0a0e17"          # deep navy-black (main background)
BG_SURFACE   = "#111827"          # card / surface layer
BG_ELEVATED  = "#1a2332"          # elevated elements (inputs, hover)
BG_HOVER     = "#1f2b3d"          # hover state for interactive items

ACCENT_START = "#06d6a0"          # primary green-cyan (Kaspersky-style)
ACCENT_END   = "#118ab2"          # blue accent for gradients
ACCENT       = ACCENT_START       # default accent color

TEXT_PRIMARY = "#e8edf5"          # main text — cool white
TEXT_SECONDARY = "#8b9bb4"        # muted / secondary text
TEXT_MUTED   = "#5a6a82"          # very subtle labels

STATUS_OK    = "#06d6a0"          # online / success green
STATUS_WARN  = "#ffd166"          # warning amber
STATUS_ERR   = "#ef476f"          # error red
INFO_BLUE    = "#118ab2"          # info blue

BORDER_SUBTLE = "#1e2a3a"         # faint border lines
DIVIDER       = "#1a2535"         # section dividers

# Solid-tint variants (CustomTkinter doesn't support alpha in hex colors)
ACCENT_TINT_1   = "#0d2f26"       # dark accent tint for active nav
ACCENT_TINT_2   = "#114035"       # slightly lighter accent tint for hover
ACCENT_BORDER   = "#0a5c48"       # accent border color
ERR_TINT        = "#2d1419"       # dark error tint for delete buttons
ERR_TINT_HOVER  = "#3d1c23"       # slightly lighter error tint for hover
ERR_BORDER      = "#6b2a37"       # error border color
OK_TINT         = "#0d2f26"       # dark success tint
OK_TINT_HOVER   = "#114035"       # slightly lighter success tint for hover
OK_BORDER       = "#0a5c48"       # success border color

# ---------------------------------------------------------------------------
# Helper widgets
# ---------------------------------------------------------------------------


class GlowBadge(ctk.CTkFrame):
    """Pill-shaped badge with a glowing dot indicator."""

    def __init__(
        self, parent: ctk.CTkBaseMixin, text: str, color: str = ACCENT_START, **kwargs
    ):
        super().__init__(
            parent, fg_color="transparent", corner_radius=20, **kwargs
        )
        # Dot indicator — small rounded frame instead of Canvas
        self._dot = ctk.CTkFrame(
            self, width=10, height=10, corner_radius=5, fg_color=color,
        )
        self._dot.pack(side="left", padx=(6, 8), pady=4)

        self._label = ctk.CTkLabel(
            self, text=text, font=("Segoe UI", 11), text_color=color,
        )
        self._label.pack(side="left", pady=3)

    def set_status(self, text: str, color: str) -> None:
        """Update the badge text and dot color."""
        self._dot.configure(fg_color=color)
        self._label.configure(text=text, text_color=color)


class TagBadge(ctk.CTkFrame):
    """Small pill-shaped tag badge."""

    def __init__(self, parent: ctk.CTkBaseMixin, text: str, **kwargs):
        super().__init__(
            parent, fg_color=ACCENT_TINT_1, corner_radius=12,
            border_width=1, border_color=ACCENT_BORDER, **kwargs
        )
        label = ctk.CTkLabel(
            self, text=f"#{text}", font=("Segoe UI Semibold", 10),
            text_color=ACCENT_START,
        )
        label.pack(side="left", padx=(8, 6), pady=3)


class SectionCard(ctk.CTkFrame):
    """Glassmorphism-style section card with subtle border."""

    def __init__(self, parent: ctk.CTkBaseMixin, title: str | None = None, **kwargs):
        corner = kwargs.pop("corner_radius", 16)
        super().__init__(
            parent,
            fg_color=BG_SURFACE,
            corner_radius=corner,
            border_width=1,
            border_color=BORDER_SUBTLE,
            **kwargs,
        )
        if title:
            header = ctk.CTkFrame(self, fg_color="transparent")
            header.pack(fill="x", padx=24, pady=(20, 6))
            ctk.CTkLabel(
                header, text=title, font=("Segoe UI Semibold", 15),
                text_color=TEXT_PRIMARY,
            ).pack(anchor="w")
            # thin accent line under title
            line = ctk.CTkFrame(header, fg_color=ACCENT_BORDER, height=2)
            line.pack(fill="x", pady=(6, 0))


# ---------------------------------------------------------------------------
# Frame: Dashboard / Editor
# ---------------------------------------------------------------------------


class DashboardFrame(ctk.CTkFrame):
    """Form for creating and saving new code snippets."""

    def __init__(
        self, parent: ctk.CTkFrame, db: "DbManager", worker: "AiWorker"
    ):
        super().__init__(parent, fg_color=BG_BASE)

        self._db = db
        self._worker = worker

        # -- Hero header -----------------------------------------------------
        hero = ctk.CTkFrame(self, fg_color="transparent")
        hero.pack(fill="x", padx=40, pady=(32, 8))

        title_lbl = ctk.CTkLabel(
            hero, text="Dashboard", font=("Segoe UI Semibold", 30),
            text_color=TEXT_PRIMARY,
        )
        title_lbl.pack(side="left")

        # Status badge
        self.status_badge = GlowBadge(hero, "Ready", color=STATUS_OK)
        self.status_badge.pack(side="right", pady=(8, 0))

        subtitle = ctk.CTkLabel(
            hero, text="Create and save code snippets with AI analysis.",
            font=("Segoe UI", 13), text_color=TEXT_SECONDARY,
        )
        subtitle.pack(anchor="w", padx=40, pady=(2, 0))

        # -- Editor card -----------------------------------------------------
        editor = SectionCard(self, "New Snippet")
        editor.pack(fill="x", padx=40, pady=(16, 0))

        # Title input
        self.title_entry = ctk.CTkEntry(
            editor, height=48, corner_radius=12, fg_color=BG_ELEVATED,
            placeholder_text="Snippet title …", font=("Segoe UI Semibold", 14),
            text_color=TEXT_PRIMARY, border_width=1, border_color=BORDER_SUBTLE,
        )
        self.title_entry.pack(fill="x", padx=24, pady=(8, 0))

        # Language row
        lang_row = ctk.CTkFrame(editor, fg_color="transparent")
        lang_row.pack(fill="x", padx=24, pady=(16, 8))

        ctk.CTkLabel(
            lang_row, text="Language:", font=("Segoe UI Semibold", 13),
            text_color=TEXT_SECONDARY,
        ).pack(side="left")

        self.lang_var = tk.StringVar(value="python")
        languages = ["python", "javascript", "typescript", "html", "css", "sql", "bash", "plaintext"]
        self.lang_dropdown = ctk.CTkOptionMenu(
            lang_row, values=languages, variable=self.lang_var,
            fg_color=BG_ELEVATED, button_color=ACCENT_START,
            dropdown_fg_color=BG_SURFACE, dropdown_hover_color=BG_HOVER,
            width=160, height=38, corner_radius=10,
        )
        self.lang_dropdown.pack(side="right")

        # Content textarea
        self.content_text = ctk.CTkTextbox(
            editor, height=280, corner_radius=12, fg_color=BG_ELEVATED,
            text_color=TEXT_PRIMARY, font=("Cascadia Code", 13),
            border_width=1, border_color=BORDER_SUBTLE,
        )
        self.content_text.pack(fill="both", expand=True, padx=24, pady=(12, 8))

        # -- Action bar ------------------------------------------------------
        action_bar = ctk.CTkFrame(self, fg_color="transparent")
        action_bar.pack(fill="x", padx=40, pady=(16, 32))

        self.save_btn = ctk.CTkButton(
            action_bar, text="Save & Analyze", font=("Segoe UI Semibold", 14),
            fg_color=ACCENT_START, hover_color="#05c090", corner_radius=12,
            height=46, width=180,
            border_width=0,
            command=self._on_save_and_analyze,
        )
        self.save_btn.pack(side="left")

        self.clear_btn = ctk.CTkButton(
            action_bar, text="Clear", font=("Segoe UI Semibold", 14),
            fg_color="transparent", hover_color=BG_HOVER, corner_radius=12,
            height=46, width=100,
            border_width=1, border_color=BORDER_SUBTLE,
            text_color=TEXT_SECONDARY,
            command=self._on_clear,
        )
        self.clear_btn.pack(side="left", padx=(12, 0))

        # -- Status bar ------------------------------------------------------
        self.status_lbl = ctk.CTkLabel(
            self, text="", font=("Segoe UI", 12), text_color=TEXT_MUTED,
        )
        self.status_lbl.pack(anchor="w", padx=40, pady=(8, 0))

    # -- handlers -----------------------------------------------------------

    def _on_save_and_analyze(self) -> None:
        title = self.title_entry.get().strip()
        content = self.content_text.get("1.0", "end-1c").strip()
        language = self.lang_var.get()

        if not title or not content:
            self._show_status("Please fill in both a title and content.", STATUS_ERR)
            return

        snippet_id = self._db.save_snippet(title, language, content)
        self._show_status(f"Snippet saved (id={snippet_id}). AI analysis starting…", ACCENT_START)
        self.save_btn.configure(state="disabled")

        pending: dict[str, bool] = {"summary": False, "tags": False}

        def on_summary(result: str, error: str | None) -> None:
            if error:
                self._show_status(f"Summary failed: {error}", STATUS_ERR)
            else:
                self._db.update_snippet_summary(snippet_id, result)
            pending["summary"] = True
            _check_done()

        def on_tags(result: str, error: str | None) -> None:
            if error:
                self._show_status(f"Tagging failed: {error}", STATUS_ERR)
            else:
                try:
                    tags = __import__("json").loads(result)
                    self._db.set_tags_for_snippet(snippet_id, tags)
                except Exception:
                    pass
            pending["tags"] = True
            _check_done()

        def _check_done() -> None:
            if pending["summary"] and pending["tags"]:
                self.save_btn.configure(state="normal")
                self._show_status(f"Snippet '{title}' saved and analyzed!", STATUS_OK)

        self._worker.summarize(content, on_summary)
        self._worker.auto_tag(content, on_tags)

    def _on_clear(self) -> None:
        self.title_entry.delete(0, "end")
        self.content_text.delete("1.0", "end")
        self.status_lbl.configure(text="")

    def _show_status(self, message: str, color: str = TEXT_MUTED) -> None:
        self.status_lbl.configure(text=message, text_color=color)


# ---------------------------------------------------------------------------
# Frame: The Vault (browse / search snippets)
# ---------------------------------------------------------------------------


class VaultFrame(ctk.CTkFrame):
    """Scrollable list of saved snippets with detail panel and search."""

    def __init__(
        self, parent: ctk.CTkFrame, db: "DbManager", worker: "AiWorker"
    ):
        super().__init__(parent, fg_color=BG_BASE)

        self._db = db
        self._worker = worker
        self._selected_id: int | None = None

        # -- Header ----------------------------------------------------------
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(32, 12))

        title_lbl = ctk.CTkLabel(
            header, text="The Vault", font=("Segoe UI Semibold", 30),
            text_color=TEXT_PRIMARY,
        )
        title_lbl.pack(side="left")

        # -- Search bar ------------------------------------------------------
        self.search_var = tk.StringVar()
        search_box = ctk.CTkEntry(
            header, placeholder_text="Search snippets …",
            textvariable=self.search_var, height=42, corner_radius=12,
            fg_color=BG_ELEVATED, width=300,
            border_width=1, border_color=BORDER_SUBTLE,
        )
        search_box.pack(side="right", padx=(0, 12))
        self.search_var.trace_add("write", lambda *_: self._refresh_list())

        # -- Import File button ----------------------------------------------
        self.import_btn = ctk.CTkButton(
            header, text="+ Import File", font=("Segoe UI Semibold", 13),
            fg_color="transparent", hover_color=BG_HOVER, corner_radius=12, height=40,
            width=140, border_width=1, border_color=BORDER_SUBTLE,
            text_color=TEXT_SECONDARY, command=self._import_file,
        )
        self.import_btn.pack(side="right")

        # -- Split panes -----------------------------------------------------
        split = ctk.CTkFrame(self, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=40, pady=(8, 32))

        # Left: snippet list
        list_frame = SectionCard(split)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.snippet_listbox = ctk.CTkTextbox(
            list_frame, wrap="word", font=("Segoe UI", 13),
            text_color=TEXT_PRIMARY, fg_color=BG_ELEVATED, corner_radius=0,
        )
        # Remove default padding from textbox
        self.snippet_listbox.pack(fill="both", expand=True, padx=0, pady=0)
        self.snippet_listbox.bind("<Double-Button-1>", self._on_double_click)

        # Right: detail panel
        detail_frame = SectionCard(split, title="Details")
        detail_frame.pack(side="right", fill="y", padx=(10, 0))
        detail_frame.configure(width=440)
        detail_frame.pack_propagate(False)

        self.detail_title = ctk.CTkLabel(
            detail_frame, text="Select a snippet", font=("Segoe UI Semibold", 18),
            text_color=TEXT_PRIMARY,
        )
        self.detail_title.pack(anchor="w", padx=24, pady=(16, 4))

        self.detail_meta = ctk.CTkLabel(
            detail_frame, text="", font=("Segoe UI", 11), text_color=TEXT_SECONDARY,
        )
        self.detail_meta.pack(anchor="w", padx=24, pady=(0, 8))

        # Summary
        self.detail_summary = ctk.CTkTextbox(
            detail_frame, height=90, wrap="word", font=("Segoe UI", 12),
            text_color=TEXT_PRIMARY, fg_color=BG_ELEVATED, corner_radius=10,
        )
        self.detail_summary.pack(fill="x", padx=24, pady=(0, 8))

        # Tags container
        tags_frame = ctk.CTkFrame(detail_frame, fg_color="transparent")
        tags_frame.pack(fill="x", padx=24, pady=(0, 8))
        self.tags_label = ctk.CTkLabel(
            tags_frame, text="Tags: ", font=("Segoe UI Semibold", 12), text_color=TEXT_SECONDARY,
        )
        self.tags_label.pack(anchor="w")

        # Content preview
        self.detail_content = ctk.CTkTextbox(
            detail_frame, height=180, wrap="word", font=("Cascadia Code", 11),
            text_color=TEXT_PRIMARY, fg_color=BG_ELEVATED, corner_radius=10,
        )
        self.detail_content.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        # Delete button
        del_btn = ctk.CTkButton(
            detail_frame, text="Delete Snippet", font=("Segoe UI Semibold", 12),
            fg_color=ERR_TINT, hover_color=ERR_TINT_HOVER, corner_radius=10, height=38,
            border_width=1, border_color=ERR_BORDER,
            text_color=STATUS_ERR, command=self._on_delete,
        )
        del_btn.pack(pady=(0, 16))

        # -- Initial load ----------------------------------------------------
        self._refresh_list()

    # -- actions ------------------------------------------------------------

    def _refresh_list(self) -> None:
        keyword = self.search_var.get().strip()
        snippets = (
            self._db.search_snippets(keyword) if keyword else self._db.get_all_snippets()
        )
        lines: list[str] = []
        for s in snippets:
            created = datetime.fromisoformat(s["created_at"]).strftime("%Y-%m-%d %H:%M")
            summary_preview = (s["summary"] or "")[:60].replace("\n", " ")
            lines.append(
                f"[{s['id']}] {s['title']}  ({s['language']}) — {created}\n"
                f"    {summary_preview}"
            )
        self.snippet_listbox.delete("1.0", "end")
        self.snippet_listbox.insert("1.0", "\n".join(lines) if lines else "No snippets yet.")

    def _on_double_click(self, event: tk.Event) -> None:
        try:
            cursor_line = int(self.snippet_listbox.index("insert").split(".")[0]) - 1
            keyword = self.search_var.get().strip()
            snippets = (
                self._db.search_snippets(keyword) if keyword else self._db.get_all_snippets()
            )
            if 0 <= cursor_line < len(snippets):
                snippet = snippets[cursor_line]
                self._show_detail(snippet["id"])
        except Exception:
            pass

    def _show_detail(self, snippet_id: int) -> None:
        snippet = self._db.get_snippet(snippet_id)
        if not snippet:
            return
        self._selected_id = snippet_id

        self.detail_title.configure(text=snippet["title"])
        created = datetime.fromisoformat(snippet["created_at"]).strftime("%Y-%m-%d %H:%M")
        self.detail_meta.configure(
            text=f"{snippet['language']}  •  Saved: {created}"
        )

        summary_text = snippet.get("summary", "") or "No summary yet."
        self.detail_summary.delete("1.0", "end")
        self.detail_summary.insert("1.0", summary_text)

        # Tags
        tags = self._db.get_tags_for_snippet(snippet_id)
        tag_widgets = [w for w in self.tags_label.winfo_children() if isinstance(w, TagBadge)]
        for w in tag_widgets:
            w.destroy()
        if tags:
            for i, tag in enumerate(tags):
                badge = TagBadge(self.tags_label, text=tag)
                badge.pack(side="left", padx=(4, 0))
        else:
            self.tags_label.configure(text="Tags: (none)")

        # Content
        self.detail_content.delete("1.0", "end")
        self.detail_content.insert("1.0", snippet["content"])

    def _on_delete(self) -> None:
        if self._selected_id is None:
            return
        if tk.messagebox.askyesno("Confirm", "Delete this snippet?"):
            self._db.delete_snippet(self._selected_id)
            self._selected_id = None
            self.detail_title.configure(text="Deleted.")
            self.detail_meta.configure(text="")
            self.detail_summary.delete("1.0", "end")
            self.detail_content.delete("1.0", "end")
            for w in self.tags_label.winfo_children():
                if isinstance(w, TagBadge):
                    w.destroy()
            self._refresh_list()

    # -- file import --------------------------------------------------------

    def _import_file(self) -> None:
        """Open a file dialog for .txt / .md / .pdf / .docx and save as snippet."""
        try:
            from tkinter.filedialog import askopenfilename  # noqa: F811
        except Exception:
            self._show_status("File dialog unavailable.", STATUS_ERR)
            return

        file_path = askopenfilename(
            title="Import File",
            filetypes=[
                ("Supported Files", "*.txt *.md *.pdf *.docx"),
                ("PDF Documents", "*.pdf"),
                ("Word Documents", "*.docx"),
                ("Markdown Files", "*.md"),
                ("Text Files", "*.txt"),
                ("All Files", "*.*"),
            ],
        )
        if not file_path:
            return

        text = self._extract_text(file_path)
        if text is None or not text.strip():
            self._show_status(
                f"'{Path(file_path).name}' — could not extract any readable text.",
                STATUS_ERR,
            )
            return

        self._save_as_snippet(file_path, text)

    def _extract_text(self, file_path: str) -> str | None:
        """Extract plain-text from *file_path*. Returns ``None`` on failure."""
        suffix = Path(file_path).suffix.lower()

        try:
            if suffix in (".txt", ".md"):
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()

            if suffix == ".pdf":
                try:
                    from pypdf import PdfReader  # noqa: F811
                except ImportError:
                    self._show_status(
                        "pypdf is not installed. Install it to import PDFs:\n"
                        "pip install pypdf",
                        STATUS_ERR,
                    )
                    return None
                reader = PdfReader(file_path)
                pages = [page.extract_text() or "" for page in reader.pages]
                return "\n\n".join(pages)

            if suffix == ".docx":
                try:
                    from docx import Document  # noqa: F811
                except ImportError:
                    self._show_status(
                        "python-docx is not installed. Install it to import .docx:\n"
                        "pip install python-docx",
                        STATUS_ERR,
                    )
                    return None
                doc = Document(file_path)
                return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

            self._show_status(
                f"Unsupported file type: {suffix}. Supported: .txt, .md, .pdf, .docx",
                STATUS_ERR,
            )
            return None

        except Exception as exc:
            logger.warning("Failed to read '%s': %s", file_path, exc)
            self._show_status(f"Error reading '{Path(file_path).name}': {exc}", STATUS_ERR)
            return None

    def _save_as_snippet(self, file_path: str, text: str) -> None:
        """Save extracted *text* as a new snippet in the database."""
        title = Path(file_path).stem
        language = Path(file_path).suffix.lstrip(".")

        snippet_id = self._db.save_snippet(title, language, text)
        self._show_status(
            f"'{title}' imported successfully (id={snippet_id}).", STATUS_OK,
        )
        self._refresh_list()
        self._show_detail(snippet_id)

    # -- public API ---------------------------------------------------------

    def highlight_snippet(self, snippet_id: int) -> None:
        """Scroll to and show a specific snippet (called from Dashboard)."""
        self._show_detail(snippet_id)

    def _show_status(self, message: str, color: str = TEXT_MUTED) -> None:
        """Show a status message at the bottom of this frame."""
        # We don't have a dedicated label here; just log for now.
        logger.info(message)


# ---------------------------------------------------------------------------
# Frame: AI Chat (Local RAG)
# ---------------------------------------------------------------------------


class ChatFrame(ctk.CTkFrame):
    """Chat interface backed by the local LLM with RAG over saved snippets."""

    def __init__(
        self, parent: ctk.CTkFrame, db: "DbManager", worker: "AiWorker"
    ):
        super().__init__(parent, fg_color=BG_BASE)

        self._db = db
        self._worker = worker
        self._chat_messages: list[dict] = []

        # -- Header ----------------------------------------------------------
        self._chat_header = ctk.CTkFrame(self, fg_color="transparent")
        self._chat_header.pack(fill="x", padx=40, pady=(32, 12))

        title_lbl = ctk.CTkLabel(
            self._chat_header, text="AI Chat", font=("Segoe UI Semibold", 30),
            text_color=TEXT_PRIMARY,
        )
        title_lbl.pack(side="left")

        # Status indicator
        self.status_indicator = GlowBadge(self._chat_header, "LLM Offline", color=STATUS_ERR)
        self.status_indicator.pack(side="right", pady=(8, 0))

        clear_btn = ctk.CTkButton(
            self._chat_header, text="Clear Chat", font=("Segoe UI Semibold", 12),
            fg_color="transparent", hover_color=BG_HOVER, corner_radius=10, height=38,
            width=110, border_width=1, border_color=BORDER_SUBTLE,
            text_color=TEXT_SECONDARY, command=self._on_clear_chat,
        )
        clear_btn.pack(side="right", padx=(0, 12))

        # -- Chat area -------------------------------------------------------
        chat_card = SectionCard(self)
        chat_card.pack(fill="both", expand=True, padx=40, pady=(8, 8))

        self.chat_display = ctk.CTkTextbox(
            chat_card, wrap="word", font=("Segoe UI", 13),
            text_color=TEXT_PRIMARY, fg_color=BG_ELEVATED, corner_radius=0,
        )
        self.chat_display.pack(fill="both", expand=True, padx=0, pady=0)
        self.chat_display.configure(state="disabled")

        # -- Input row -------------------------------------------------------
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=40, pady=(0, 32))

        self.chat_entry = ctk.CTkEntry(
            input_frame, placeholder_text="Ask about your saved snippets …",
            height=48, corner_radius=16, fg_color=BG_ELEVATED,
            border_width=1, border_color=BORDER_SUBTLE,
        )
        self.chat_entry.pack(side="left", fill="x", expand=True)
        self.chat_entry.bind("<Return>", lambda _e: self._on_send())

        send_btn = ctk.CTkButton(
            input_frame, text="Send", font=("Segoe UI Semibold", 14),
            fg_color=ACCENT_START, hover_color="#05c090", corner_radius=16,
            height=48, width=100, border_width=0,
            command=self._on_send,
        )
        send_btn.pack(side="right", padx=(12, 0))

        # -- Restore history & check LLM -------------------------------------
        self._restore_history()
        self._check_llm_status()

    # -- actions ------------------------------------------------------------

    def _check_llm_status(self) -> None:
        if self._worker.is_available():
            self.status_indicator.set_status("LLM Online", STATUS_OK)
        else:
            self.status_indicator.set_status("LLM Offline", STATUS_ERR)

    def _restore_history(self) -> None:
        history = self._db.get_chat_history()
        for msg in history:
            self._append_message(msg["role"], msg["content"])

    def _on_send(self) -> None:
        text = self.chat_entry.get().strip()
        if not text:
            return
        self.chat_entry.delete(0, "end")

        self._append_message("user", text)
        self._chat_messages.append({"role": "user", "content": text})
        self._db.append_chat_message("user", text)

        rag_context = self._build_rag_context(text)

        messages = list(self._chat_messages)
        if rag_context:
            messages.insert(0, {
                "role": "system",
                "content": "Relevant snippets from the knowledge base:\n\n" + rag_context,
            })

        def on_chat_result(result: str, error: str | None) -> None:
            if error:
                self._append_message("assistant", f"[Error] {error}")
            else:
                self._chat_messages.append({"role": "assistant", "content": result})
                self._db.append_chat_message("assistant", result)
                self._append_message("assistant", result)

        if not self._worker.is_available():
            on_chat_result("", "LM Studio is not running. Start it and try again.")
            return

        self._worker.chat(messages, on_chat_result)

    def _build_rag_context(self, query: str) -> str:
        results = self._db.search_snippets(query)[:5]
        if not results:
            return ""
        parts: list[str] = []
        for s in results:
            summary = s.get("summary", "") or "No summary available."
            title = s["title"]
            lang = s["language"]
            content_preview = s["content"][:500].replace("\n", " ")
            parts.append(
                f"Snippet: {title} ({lang})\nSummary: {summary}\nContent: {content_preview}"
            )
        return "\n\n---\n\n".join(parts)

    def _on_clear_chat(self) -> None:
        self._chat_messages.clear()
        self._db.clear_chat_history()
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")

    # -- display helper -----------------------------------------------------

    def _append_message(self, role: str, content: str) -> None:
        """Append a message to the chat display with styling."""
        self.chat_display.configure(state="normal")
        prefix = "🧑 You" if role == "user" else "🤖 AI"

        # Color-coded role label
        self.chat_display.insert("end", f"\n{'─'*40}\n", ("sep",))
        self.chat_display.insert("end", f"{prefix}  •  ", ("role",))
        self.chat_display.insert("end", content + "\n\n")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")


# ---------------------------------------------------------------------------
# Frame: Settings
# ---------------------------------------------------------------------------


class SettingsFrame(ctk.CTkFrame):
    """Application settings — LLM endpoint, temperature, timeouts, etc."""

    def __init__(
        self, parent: ctk.CTkFrame, db: "DbManager", worker: "AiWorker",
        settings_mgr: "SettingsManager",
    ):
        super().__init__(parent, fg_color=BG_BASE)

        self._db = db
        self._worker = worker
        self._settings = settings_mgr

        # -- Header ----------------------------------------------------------
        title_lbl = ctk.CTkLabel(
            self, text="Settings", font=("Segoe UI Semibold", 30),
            text_color=TEXT_PRIMARY,
        )
        title_lbl.pack(anchor="w", padx=40, pady=(32, 4))

        subtitle = ctk.CTkLabel(
            self, text="Configure LLM connection, AI parameters, and app behavior.",
            font=("Segoe UI", 13), text_color=TEXT_SECONDARY,
        )
        subtitle.pack(anchor="w", padx=40, pady=(0, 20))

        # -- Card: LLM Connection --------------------------------------------
        llm_card = SectionCard(self, "LLM Connection")
        llm_card.pack(fill="x", padx=40, pady=(0, 16))

        ctk.CTkLabel(
            llm_card, text="Endpoint URL:", font=("Segoe UI Semibold", 13),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", padx=24, pady=(16, 6))

        self.endpoint_var = tk.StringVar(value=self._settings.get_endpoint())
        ctk.CTkEntry(
            llm_card, textvariable=self.endpoint_var, height=44, corner_radius=10,
            fg_color=BG_ELEVATED, border_width=1, border_color=BORDER_SUBTLE,
            placeholder_text="http://127.0.0.1:1234/v1",
        ).pack(fill="x", padx=24, pady=(0, 6))

        # -- Card: AI Parameters ---------------------------------------------
        ai_card = SectionCard(self, "AI Parameters")
        ai_card.pack(fill="x", padx=40, pady=(0, 16))

        row1 = ctk.CTkFrame(ai_card, fg_color="transparent")
        row1.pack(fill="x", padx=24, pady=(16, 8))

        # Temperature
        temp_frame = ctk.CTkFrame(row1, fg_color="transparent")
        temp_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            temp_frame, text="Temperature:", font=("Segoe UI Semibold", 12),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w")
        self.temp_var = tk.DoubleVar(value=self._settings.get_temperature())
        ctk.CTkEntry(
            temp_frame, textvariable=self.temp_var, height=38, corner_radius=10,
            fg_color=BG_ELEVATED, border_width=1, border_color=BORDER_SUBTLE,
            placeholder_text="0.0 – 2.0",
        ).pack(fill="x", pady=(4, 0))

        # Max Tokens
        tokens_frame = ctk.CTkFrame(row1, fg_color="transparent")
        tokens_frame.pack(side="left", fill="x", expand=True, padx=(16, 0))
        ctk.CTkLabel(
            tokens_frame, text="Max Tokens:", font=("Segoe UI Semibold", 12),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w")
        self.max_tokens_var = tk.IntVar(value=self._settings.get_max_tokens())
        ctk.CTkEntry(
            tokens_frame, textvariable=self.max_tokens_var, height=38, corner_radius=10,
            fg_color=BG_ELEVATED, border_width=1, border_color=BORDER_SUBTLE,
            placeholder_text="64 – 8192",
        ).pack(fill="x", pady=(4, 0))

        # Request Timeout
        row2 = ctk.CTkFrame(ai_card, fg_color="transparent")
        row2.pack(fill="x", padx=24, pady=(8, 16))

        timeout_frame = ctk.CTkFrame(row2, fg_color="transparent")
        timeout_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            timeout_frame, text="Request Timeout (s):", font=("Segoe UI Semibold", 12),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w")
        self.timeout_var = tk.IntVar(value=self._settings.get_request_timeout())
        ctk.CTkEntry(
            timeout_frame, textvariable=self.timeout_var, height=38, corner_radius=10,
            fg_color=BG_ELEVATED, border_width=1, border_color=BORDER_SUBTLE,
            placeholder_text="5 – 600",
        ).pack(fill="x", pady=(4, 0))

        # -- Card: Chat ------------------------------------------------------
        chat_card = SectionCard(self, "Chat")
        chat_card.pack(fill="x", padx=40, pady=(0, 16))

        history_frame = ctk.CTkFrame(chat_card, fg_color="transparent")
        history_frame.pack(fill="x", padx=24, pady=(16, 16))
        ctk.CTkLabel(
            history_frame, text="Chat History Limit:", font=("Segoe UI Semibold", 12),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w")
        self.history_limit_var = tk.IntVar(value=self._settings.get_chat_history_limit())
        ctk.CTkEntry(
            history_frame, textvariable=self.history_limit_var, height=38, corner_radius=10,
            fg_color=BG_ELEVATED, border_width=1, border_color=BORDER_SUBTLE,
            placeholder_text="1 – 500",
        ).pack(fill="x", pady=(4, 0))

        # -- Card: Actions ---------------------------------------------------
        action_card = SectionCard(self, "Actions")
        action_card.pack(fill="x", padx=40, pady=(0, 16))

        btn_row = ctk.CTkFrame(action_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(16, 16))

        self.test_btn = ctk.CTkButton(
            btn_row, text="Test Connection", font=("Segoe UI Semibold", 13),
            fg_color=ACCENT_START, hover_color="#05c090", corner_radius=12, height=44,
            width=160, border_width=0, command=self._on_test_connection,
        )
        self.test_btn.pack(side="left")

        self.save_btn = ctk.CTkButton(
            btn_row, text="Save Settings", font=("Segoe UI Semibold", 13),
            fg_color=OK_TINT, hover_color=OK_TINT_HOVER, corner_radius=12, height=44,
            width=160, border_width=1, border_color=OK_BORDER,
            text_color=STATUS_OK, command=self._on_save_settings,
        )
        self.save_btn.pack(side="left", padx=(12, 0))

        # -- Status label ----------------------------------------------------
        self.status_lbl = ctk.CTkLabel(
            self, text="", font=("Segoe UI", 12), text_color=TEXT_MUTED,
        )
        self.status_lbl.pack(anchor="w", padx=40, pady=(8, 32))

    # -- helpers ------------------------------------------------------------

    # -- actions ------------------------------------------------------------

    def _on_test_connection(self) -> None:
        endpoint = self.endpoint_var.get().strip()
        if not endpoint:
            self._show_status("Please enter an endpoint URL.", STATUS_ERR)
            return

        self.test_btn.configure(state="disabled", text="Testing…")
        self.status_lbl.configure(text="", text_color=TEXT_MUTED)

        def check() -> None:
            try:
                import requests as req
                resp = req.get(f"{endpoint}/models", timeout=5)
                if resp.ok:
                    self._show_status("Connection successful! LLM is reachable.", STATUS_OK)
                else:
                    self._show_status(
                        f"Server responded with status {resp.status_code}.", STATUS_ERR,
                    )
            except Exception:
                self._show_status(
                    "Connection failed — check the URL and that LM Studio is running.",
                    STATUS_ERR,
                )
            finally:
                self.test_btn.configure(state="normal", text="Test Connection")

        self.after(50, check)

    def _on_save_settings(self) -> None:
        endpoint = self.endpoint_var.get().strip()
        if not endpoint:
            self._show_status("Endpoint URL cannot be empty.", STATUS_ERR)
            return

        try:
            temperature = float(self.temp_var.get())
            max_tokens = int(self.max_tokens_var.get())
            timeout = int(self.timeout_var.get())
            history_limit = int(self.history_limit_var.get())
        except ValueError:
            self._show_status("Please enter valid numbers for all numeric fields.", STATUS_ERR)
            return

        self._settings.set_llm_endpoint(endpoint)
        self._settings.set_temperature(temperature)
        self._settings.set_max_tokens(max_tokens)
        self._settings.set_request_timeout(timeout)
        self._settings.set_chat_history_limit(history_limit)

        self._settings.save()

        self._show_status("Settings saved successfully!", STATUS_OK)

    def _show_status(self, message: str, color: str = TEXT_MUTED) -> None:
        self.status_lbl.configure(text=message, text_color=color)


# ---------------------------------------------------------------------------
# Main Application Window
# ---------------------------------------------------------------------------


class NeuroVaultApp(ctk.CTk):
    """Top-level application window with sidebar navigation."""

    def __init__(
        self, db: "DbManager", worker: "AiWorker",
        settings_mgr: "SettingsManager | None" = None,
    ):
        super().__init__()

        self._db = db
        self._worker = worker

        # -- Window setup ----------------------------------------------------
        self.title("NeuroVault Pro")
        self.geometry("1280x780")
        self.minsize(960, 640)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # -- Layout ----------------------------------------------------------
        main_frame = ctk.CTkFrame(self, fg_color=BG_BASE)
        main_frame.pack(fill="both", expand=True)

        # Sidebar — glass panel
        sidebar = ctk.CTkFrame(
            main_frame, width=240, fg_color=BG_SURFACE, corner_radius=0,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Accent strip on left edge of sidebar
        accent_strip = ctk.CTkFrame(sidebar, width=3, fg_color=ACCENT_START)
        accent_strip.pack(side="left", fill="y")

        # Logo / App title area
        logo_area = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_area.pack(fill="x", pady=(28, 16))

        # Icon circle
        icon_circle = ctk.CTkFrame(
            logo_area, width=48, height=48, corner_radius=24,
            fg_color=ACCENT_TINT_1,
        )
        icon_circle.pack(side="left", padx=(20, 12))
        ctk.CTkLabel(
            icon_circle, text="🔐", font=("Segoe UI Emoji", 22),
        ).pack(expand=True)

        app_title = ctk.CTkLabel(
            logo_area, text="NeuroVault", font=("Segoe UI Semibold", 18),
            text_color=TEXT_PRIMARY,
        )
        app_title.pack(side="left", pady=(4, 0))
        app_pro = ctk.CTkLabel(
            logo_area, text=" Pro", font=("Segoe UI", 12),
            text_color=ACCENT_START,
        )
        app_pro.pack(side="left", pady=(8, 0))

        # Nav buttons area
        nav_container = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_container.pack(fill="x", padx=12, pady=(8, 0))

        self._nav_buttons: list[ctk.CTkButton] = []
        nav_items = [
            ("Dashboard",   "📊",  self._show_dashboard),
            ("The Vault",   "🗄️",  self._show_vault),
            ("AI Chat",     "💬",  self._show_chat),
            ("Settings",    "⚙️",  self._show_settings),
        ]
        for label, icon, cmd in nav_items:
            btn = ctk.CTkButton(
                nav_container, text=f"  {icon}  {label}", font=("Segoe UI Semibold", 14),
                height=46, corner_radius=12, anchor="w", command=cmd,
                fg_color="transparent", hover_color=BG_HOVER,
                border_width=0,
                text_color=TEXT_SECONDARY,
            )
            btn.pack(fill="x", pady=3)
            self._nav_buttons.append(btn)

        # Bottom info in sidebar
        bottom_info = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom_info.pack(side="bottom", fill="x", pady=(0, 20))
        version_lbl = ctk.CTkLabel(
            bottom_info, text="v1.0.0", font=("Segoe UI", 10),
            text_color=TEXT_MUTED,
        )
        version_lbl.pack(anchor="center")

        # Content area
        content_frame = ctk.CTkFrame(main_frame, fg_color=BG_BASE)
        content_frame.pack(side="left", fill="both", expand=True, padx=0)

        self._dashboard_page = DashboardFrame(content_frame, db, worker)
        self._vault_page     = VaultFrame(content_frame, db, worker)
        self._chat_page      = ChatFrame(content_frame, db, worker)
        sm = settings_mgr if settings_mgr is not None else SettingsManager()
        self._settings_page  = SettingsFrame(content_frame, db, worker, sm)

        # Only Dashboard packed initially
        self._dashboard_page.pack(fill="both", expand=True)
        self._current_page: ctk.CTkFrame = self._dashboard_page

    # -- navigation ---------------------------------------------------------

    def _swap_page(self, new_page: ctk.CTkFrame) -> None:
        if new_page is not self._current_page:
            self._current_page.pack_forget()
            new_page.pack(fill="both", expand=True)
            self._current_page = new_page

    def _show_dashboard(self) -> None:
        self._swap_page(self._dashboard_page)
        self._set_active_nav(0)

    def _show_vault(self) -> None:
        self._swap_page(self._vault_page)
        self._vault_page._refresh_list()
        self._set_active_nav(1)

    def _show_chat(self) -> None:
        self._swap_page(self._chat_page)
        self._set_active_nav(2)

    def _show_settings(self) -> None:
        self._swap_page(self._settings_page)
        self._set_active_nav(3)

    def _set_active_nav(self, index: int) -> None:
        for i, btn in enumerate(self._nav_buttons):
            if i == index:
                btn.configure(
                    fg_color=ACCENT_TINT_1,
                    hover_color=ACCENT_TINT_2,
                    text_color=ACCENT_START,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    hover_color=BG_HOVER,
                    text_color=TEXT_SECONDARY,
                )
