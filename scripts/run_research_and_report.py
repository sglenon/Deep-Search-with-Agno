import os
import sys
from pathlib import Path

# Add the parent directory to the Python path to enable relative imports
sys.path.append(str(Path(__file__).parent.parent))

from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory

from chains.research_and_report_workflow import build_research_and_report_workflow
from prompts.research_and_report_prompts import (
    get_adviser_instructions as ADVISER_INSTRUCTIONS,
)
from prompts.research_and_report_prompts import (
    get_compiler_instructions as COMPILER_INSTRUCTIONS,
)
from prompts.research_and_report_prompts import (
    get_researcher_instructions as RESEARCHER_INSTRUCTIONS,
)

# === Setup ===
memory_db = SqliteMemoryDb(table_name="memory", db_file="tmp/memory.db")
memory = Memory(db=memory_db)


def agent_id(user_id: str, role: str) -> str:
    return f"{user_id}:{role}"


user_id = "user_id"
query = "machine learning for coordination compounds"

# === Build and Run Workflow ===
workflow = build_research_and_report_workflow(
    llm=os.getenv("llm"),
    memory=memory,
    agent_id=agent_id,
    user_id=user_id,
    ADVISER_INSTRUCTIONS=ADVISER_INSTRUCTIONS,
    RESEARCHER_INSTRUCTIONS=RESEARCHER_INSTRUCTIONS,
    COMPILER_INSTRUCTIONS=COMPILER_INSTRUCTIONS,
)

topic_response = workflow.print_response(query, markdown=True)
print(topic_response)
