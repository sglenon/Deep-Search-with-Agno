# ruff: noqa: E402
import asyncio
import inspect
import json
import os
import sys

from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.workflow.v2 import Parallel, Step, Workflow
from dotenv import find_dotenv, load_dotenv

# Ensure project root is on sys.path for direct script execution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# === Import prompts and agents ===

from agents.research_and_report_agents import (
    create_adviser_agent,
    create_compiler_agent,
    extract_json_step,
    get_report_step,
    make_researcher,
)

# === Import prompts for standalone execution ===
from prompts.research_and_report_prompts import (
    get_adviser_instructions as ADVISER_INSTRUCTIONS,
)
from prompts.research_and_report_prompts import (
    get_compiler_instructions as COMPILER_INSTRUCTIONS,
)
from prompts.research_and_report_prompts import (
    get_researcher_instructions as RESEARCHER_INSTRUCTIONS,
)

# === Load Environment ===
load_dotenv(find_dotenv())
llm = os.getenv("llm")
api_key = os.getenv("OPENAI_API_KEY")
if api_key is None:
    raise EnvironmentError("OPENAI_API_KEY not found in .env file")

# === Memory ===
memory_db = SqliteMemoryDb(table_name="memory", db_file="tmp/memory.db")
memory = Memory(db=memory_db)


def agent_id(user_id: str, role: str) -> str:
    return f"{user_id}:{role}"


# === Defaults ===
user_id = "user_id"  # replace dynamically if needed
query = "machine learning for coordination compounds"
citation_style = "american chemical society"


# === FunctionStep wrapper for callable steps ===
class SimpleResponse:
    def __init__(self, content: str):
        self.content = content


class FunctionStep:
    def __init__(self, func):
        self.func = func

    def run(self, message=None, **kwargs):
        """
        Adapter executor to let plain functions (sync or async) run inside
        an Agno Step. It normalizes the inputs coming from the previous step.

        Behavior:
        - If the underlying function is sync (e.g., extract_json_step), we pass a string.
        - If it's async (e.g., get_report_step), we pass a dict as `inputs`.
        """
        # Prefer structured inputs if provided
        inputs = kwargs.get("inputs")
        if inputs is None:
            # If the previous step returned an object with `.content`, use it
            if hasattr(message, "content"):
                raw = message.content
                if isinstance(raw, str):
                    stripped = raw.strip()
                    if stripped.startswith("{"):
                        try:
                            inputs = json.loads(stripped)
                        except Exception:
                            inputs = None
                elif isinstance(raw, dict):
                    inputs = raw
            elif isinstance(message, dict):
                inputs = message
            elif isinstance(message, str):
                stripped = message.strip()
                if stripped.startswith("{"):
                    try:
                        inputs = json.loads(stripped)
                    except Exception:
                        inputs = None

        # If the function is async, pass a dict (default to {})
        if inspect.iscoroutinefunction(self.func):
            payload = inputs if isinstance(inputs, dict) else {}
            # Enrich payload with the global query if links are present
            try:
                if "url_links" in payload and "query" not in payload:
                    payload["query"] = query
            except Exception:
                pass
            # Execute coroutine
            try:
                result = asyncio.run(self.func(payload))
            except RuntimeError as e:
                # Fallback if already inside an event loop
                if "asyncio.run() cannot be called" in str(e):
                    loop = asyncio.get_event_loop()
                    result = loop.run_until_complete(self.func(payload))
                else:
                    raise
            # Normalize result to SimpleResponse
            try:
                content_str = (
                    json.dumps(result) if not isinstance(result, str) else result
                )
            except Exception:
                content_str = str(result)
            return SimpleResponse(content=content_str)

        # Otherwise, call sync function with a string message
        if isinstance(message, str):
            text = message
        elif isinstance(inputs, dict):
            # Best-effort: if previous output is dict, pass its string form
            text = json.dumps(inputs)
        else:
            text = "" if message is None else str(message)
        result = self.func(text)
        # Normalize to SimpleResponse so Step._process_step_output can read `.content`
        try:
            content_str = json.dumps(result) if not isinstance(result, str) else result
        except Exception:
            content_str = str(result)
        return SimpleResponse(content=content_str)


# === Workflow Builder ===
def build_research_and_report_workflow(
    llm,
    memory,
    agent_id,
    user_id,
    ADVISER_INSTRUCTIONS,
    RESEARCHER_INSTRUCTIONS,
    COMPILER_INSTRUCTIONS,
):
    Adviser = create_adviser_agent(
        llm,
        memory,
        agent_id,
        user_id,
        "Expert research adviser with decades of publishing experience.",
        ADVISER_INSTRUCTIONS().format(query=query),
    )

    Compiler = create_compiler_agent(
        llm,
        memory,
        agent_id,
        user_id,
        "Compiles research findings and drafts the report.",
        COMPILER_INSTRUCTIONS(),
    )

    researchers = [
        make_researcher(
            llm,
            memory,
            agent_id,
            user_id,
            subtopic_index=i,
            researcher_instructions=RESEARCHER_INSTRUCTIONS().format(subtopic_index=i),
        )
        for i in range(4)
    ]

    # Extract = extract_json_step
    # Report = get_report_step

    return Workflow(
        name="Researach + Report Pipeline",
        steps=[
            Step(name="Planning", agent=Adviser),
            Parallel(
                *[
                    Step(name=f"Agent {i + 1}", agent=researchers[i])
                    for i in range(len(researchers))
                ],
                name="Research Phase",
            ),
            Step(name="Compiler", agent=Compiler),
            Step(name="Extract Links", agent=FunctionStep(extract_json_step)),
            Step(name="Report Maker", agent=FunctionStep(get_report_step)),
        ],
    )


# === Standalone runner ===
if __name__ == "__main__":
    workflow = build_research_and_report_workflow(
        llm=llm,
        memory=memory,
        agent_id=agent_id,
        user_id=user_id,
        ADVISER_INSTRUCTIONS=ADVISER_INSTRUCTIONS,
        RESEARCHER_INSTRUCTIONS=RESEARCHER_INSTRUCTIONS,
        COMPILER_INSTRUCTIONS=COMPILER_INSTRUCTIONS,
    )
    topic_response = workflow.print_response(query, markdown=True)
    print(topic_response)
