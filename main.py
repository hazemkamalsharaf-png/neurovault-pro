"""
main.py — Entry point for NeuroVault Pro.

Initialises the database, settings, AI worker thread, and launches the
CustomTkinter application loop.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure the package directory is on sys.path so imports resolve when run directly
_PACKAGE_DIR = Path(__file__).resolve().parent
if str(_PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_DIR))

import customtkinter as ctk

from ai_worker import AiWorker
from db_manager import DbManager
from gui import NeuroVaultApp
from settings import SettingsManager


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("neurovault")


def main() -> None:
    """Bootstrap and run NeuroVault Pro."""

    # -- Settings ------------------------------------------------------------
    settings_path = _PACKAGE_DIR / "data" / "settings.json"
    settings_mgr = SettingsManager(settings_path)
    logger.info("Settings loaded — endpoint: %s", settings_mgr.get_endpoint())

    # -- Database ----------------------------------------------------------
    db_path = _PACKAGE_DIR / "data" / "neurovault.db"
    logger.info("Database path: %s", db_path)
    db = DbManager(db_path)
    db.init_schema()  # idempotent — creates tables if missing

    # -- AI Worker ---------------------------------------------------------
    worker = AiWorker(settings_manager=settings_mgr)
    worker.start()
    logger.info("AI worker thread started.")

    # -- UI ----------------------------------------------------------------
    app = NeuroVaultApp(db=db, worker=worker, settings_mgr=settings_mgr)

    # Periodically check LLM availability (every 5 seconds) so the status
    # indicator updates when LM Studio is started or stopped.
    def _poll_llm() -> None:
        if hasattr(app, "_chat_page"):
            app._chat_page._check_llm_status()
        app.after(5000, _poll_llm)

    app.after(2000, _poll_llm)  # first check after 2 s

    # -- Run ---------------------------------------------------------------
    logger.info("Starting UI…")
    app.mainloop()

    # Cleanup
    worker.stop()
    logger.info("Shut down complete.")


if __name__ == "__main__":
    main()
