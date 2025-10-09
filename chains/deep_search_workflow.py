import os
import sys

from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.workflow.v2 import Parallel, Step, Workflow
from dotenv import find_dotenv, load_dotenv

# === Import modularized agents ===
from agents.deep_search_agents import (
    create_adviser_agent,
    create_citation_agent,
    create_supervisor_agent,
    make_researcher,
)

# === Import prompts ===
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
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load environment
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
user_id = "user_id"  # replace dynamically if needed"
citation_style = "american psychological association"
query = "machine learning for coordination compounds"


# === Workflow Builder ===
def build_deep_search_workflow(
    llm,
    memory,
    agent_id,
    user_id,
    ADVISER_INSTRUCTIONS,
    RESEARCHER_INSTRUCTIONS,
    SUPERVISOR_INSTRUCTIONS,
    SUPERVISOR2_INSTRUCTIONS,
    CITATION_INSTRUCTIONS,
    citation_style,
    citation_guides_folder,
):
    Adviser = create_adviser_agent(
        llm,
        memory,
        agent_id,
        user_id,
        "Expert research adviser with decades of publishing experience.",
        ADVISER_INSTRUCTIONS(query=query, citation_style=citation_style),
    )

    Researcher1 = make_researcher(
        llm,
        memory,
        agent_id,
        user_id,
        subtopic_index=1,
        researcher_instructions=RESEARCHER_INSTRUCTIONS(subtopic_index=1),
    )
    Researcher2 = make_researcher(
        llm,
        memory,
        agent_id,
        user_id,
        subtopic_index=2,
        researcher_instructions=RESEARCHER_INSTRUCTIONS(subtopic_index=2),
    )
    Researcher3 = make_researcher(
        llm,
        memory,
        agent_id,
        user_id,
        subtopic_index=3,
        researcher_instructions=RESEARCHER_INSTRUCTIONS(subtopic_index=3),
    )

    Supervisor = create_supervisor_agent(
        llm,
        memory,
        agent_id,
        user_id,
        "Supervisor for synthesizing results.",
        SUPERVISOR_INSTRUCTIONS(),
    )
    Supervisor2 = create_supervisor_agent(
        llm,
        memory,
        agent_id,
        user_id,
        "Supervisor for cleanup and refinement.",
        SUPERVISOR2_INSTRUCTIONS(),
    )
    Citation = create_citation_agent(
        llm,
        memory,
        agent_id,
        user_id,
        "Formats results into proper citations.",
        CITATION_INSTRUCTIONS(citation_style=citation_style,
            citation_guides_folder=citation_guides_folder))

    return Workflow(
        name="Deep Search Pipeline",
        workflow_id="deep_search_team",
        steps=[
            Step(name="Planning", agent=Adviser),
            Parallel(
                Step(name="Agent 1", agent=Researcher1),
                Step(name="Agent 2", agent=Researcher2),
                Step(name="Agent 3", agent=Researcher3),
                name="Research Phase",
            ),
            Step(name="Synthesis", agent=Supervisor),
            Step(name="Cleanup", agent=Supervisor2),
            Step(name="Formatting", agent=Citation),
        ],
    # === Patch: Validate researcher outputs before aggregation ===
    # This assumes the workflow engine allows post-processing hooks or can be adapted to do so.
    # If not, this logic should be integrated into the agent or step execution.
    # Example for a custom workflow engine:
    # for step in workflow.steps:
    #     if step.name.startswith("Agent"):
    #         step.output = validate_researcher_output(step.output)
    # If using a framework, adapt as needed to ensure validation is applied before Supervisor step.
    )
# === Validation Utility ===
import re

def validate_researcher_output(output: str) -> str:
    """Validate researcher output for required tables, equations, and reference DOIs/URLs."""
    warnings = []
    # Check for Markdown pipe table
    if not re.search(r"^\s*\|.*\|", output, re.MULTILINE):
        warnings.append("> **Warning:** Required Markdown table is missing.")
    # Check for Unicode box-drawing characters
    if re.search(r"[┃━╭╮╯╰]", output):
        warnings.append("> **Warning:** Table format is incorrect.")
    # Check for LaTeX equations
    if not re.search(r"\$.*?\$|\$\$.*?\$\$", output, re.DOTALL):
        if "> **Note:** No equations are relevant for this subtopic." not in output:
            warnings.append("> **Warning:** No LaTeX equations found and no justification provided.")
    # Check references for DOI/URL
    ref_lines = [line for line in output.splitlines() if re.match(r"^\s*[\d•]\s+[A-Z][a-zA-Z]+,", line)]
    missing_doi = False
    for line in ref_lines:
        if not re.search(r"(doi\.org|http[s]?://)", line):
            missing_doi = True
            break
    if missing_doi and "> **Warning:** Some references are missing DOIs or URLs." not in output:
        warnings.append("> **Warning:** Some references are missing DOIs or URLs.")
    # Append warnings at the end
    if warnings:
        output = output.rstrip() + "\n" + "\n".join(warnings)
    return output


# === Run Workflow (for standalone execution) ===
if __name__ == "__main__":
    workflow = build_deep_search_workflow(
        llm,
        memory,
        agent_id,
        user_id,
        ADVISER_INSTRUCTIONS,
        RESEARCHER_INSTRUCTIONS,
        SUPERVISOR_INSTRUCTIONS,
        SUPERVISOR2_INSTRUCTIONS,
        CITATION_INSTRUCTIONS,
        citation_style,
        os.path.join(PROJECT_ROOT, "tools", "citation_guides"),
    )
    topic_response = workflow.print_response(query, markdown=True)
    print(topic_response)
