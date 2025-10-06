# scripts/run_deep_search.py

import os
import sys
import logging
import datetime
from pathlib import Path
from dotenv import load_dotenv
from queue import Queue
from logging.handlers import QueueHandler, QueueListener
import atexit

# === Load environment variables ===
load_dotenv()
# === Logging Setup ===
def setup_logging():
    """
    Configures asynchronous logging to file and stdout.
    Logs are written asynchronously to logs/ (relative to project root).
    If the log directory cannot be created or is not writable, aborts execution.
    Ensures async writing to both console and file.
    Also redirects sys.stdout and sys.stderr to the logger.
    """
    logger = logging.getLogger()
    if getattr(logger, "_async_logging_setup", False):
        return logger  # Prevent duplicate handlers

    # --- Log directory: logs/ ---
    logs_dir = Path(__file__).resolve().parent.parent / "logs"

    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        # Check if directory is writable
        test_file = logs_dir / ".write_test"
        with open(test_file, "w") as f:
            f.write("test")
        test_file.unlink()
    except Exception as e:
        print(f"[ERROR] Failed to create or write to log directory '{logs_dir}': {e}", file=sys.stderr)
        sys.exit(1)

    # Use a unique log file per run: include date and time down to seconds
    log_file = logs_dir / f"run_deep_search_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

    # --- Asynchronous logging setup ---
    log_queue = Queue(-1)
    file_handler = logging.FileHandler(log_file, encoding="utf-8", delay=False)
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    # QueueListener will handle both file and stream handlers
    listener = QueueListener(log_queue, file_handler, stream_handler, respect_handler_level=True)
    listener.start()
    atexit.register(listener.stop)

    # Set up root logger with QueueHandler
    queue_handler = QueueHandler(log_queue)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[queue_handler],
        force=True,
    )

    logger._async_logging_setup = True  # Mark as set up

    logging.info("=== Script run_deep_search.py started ===")
    logging.info(f"Logs are being written asynchronously to: {log_file}")

    # --- Redirect unhandled exceptions ---
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

    # --- Redirect stdout/stderr to logger asynchronously ---
    class LoggerWriter:
        def __init__(self, level):
            self.level = level
            self._buffer = ""
        def write(self, message):
            if message and not message.isspace():
                for line in message.rstrip().splitlines():
                    self.level(line.rstrip())
        def flush(self):
            pass

    sys.stdout = LoggerWriter(logging.getLogger().info)
    sys.stderr = LoggerWriter(logging.getLogger().error)

    return logger


setup_logging()

# === Project Path Setup ===
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from chains.deep_search_workflow import build_deep_search_workflow
from prompts.deep_search_prompts import (
    get_adviser_instructions as ADVISER_INSTRUCTIONS,
    get_citation_instructions as CITATION_INSTRUCTIONS,
    get_researcher_instructions as RESEARCHER_INSTRUCTIONS,
    get_supervisor2_instructions as SUPERVISOR2_INSTRUCTIONS,
    get_supervisor_instructions as SUPERVISOR_INSTRUCTIONS,
)

# === Setup ===
memory_db = SqliteMemoryDb(table_name="memory", db_file="tmp/memory.db")
memory = Memory(db=memory_db)

def agent_id(user_id: str, role: str) -> str:
    return f"{user_id}:{role}"

user_id = "user_id"
query = "machine learning for coordination compounds"
citation_style = "american chemical society"
citation_guides_folder = PROJECT_ROOT / "tools" / "citation_guides"

# === Build and Run Workflow ===
try:
    logging.info("Initializing workflow...")
    workflow = build_deep_search_workflow(
        llm=os.getenv("llm"),
        memory=memory,
        agent_id=agent_id,
        user_id=user_id,
        ADVISER_INSTRUCTIONS=ADVISER_INSTRUCTIONS,
        RESEARCHER_INSTRUCTIONS=RESEARCHER_INSTRUCTIONS,
        SUPERVISOR_INSTRUCTIONS=SUPERVISOR_INSTRUCTIONS,
        SUPERVISOR2_INSTRUCTIONS=SUPERVISOR2_INSTRUCTIONS,
        CITATION_INSTRUCTIONS=CITATION_INSTRUCTIONS,
        citation_style=citation_style,
        citation_guides_folder=citation_guides_folder,
    )

    topic_response = workflow.print_response(query, markdown=True)
    logging.info("Workflow executed successfully.")
    logging.info(f"Response:\n{topic_response}")

except Exception as e:
    logging.error("An error occurred during workflow execution: %s", str(e), exc_info=True)
    raise
