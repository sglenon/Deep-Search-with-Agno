# scripts/run_deep_search.py

import os
import sys
# Ensure project root is on PYTHONPATH
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory

from chains.deep_search_workflow import build_deep_search_workflow
from prompts.deep_search_prompts import (
    get_adviser_instructions as ADVISER_INSTRUCTIONS,
)
from prompts.deep_search_prompts import (
    get_citation_instructions as CITATION_INSTRUCTIONS,
)
from prompts.deep_search_prompts import (
    get_researcher_instructions as RESEARCHER_INSTRUCTIONS,
)
from prompts.deep_search_prompts import (
    get_supervisor2_instructions as SUPERVISOR2_INSTRUCTIONS,
)
from prompts.deep_search_prompts import (
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
citation_guides_folder = os.path.join(PROJECT_ROOT, "tools", "citation_guides")

# === Build and Run Workflow ===
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
print(topic_response)
