import os
import sys
from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.arxiv import ArxivTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.googlesearch import GoogleSearchTools
from agno.tools.hackernews import HackerNewsTools

from tools.philippines_search_tool import PhilippinesSearchTool
from tools.sci_paper_search_tool import SciResTool

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# === Adviser Agent ===
def create_adviser_agent(llm, memory, agent_id, user_id, description, instructions):
    """
    Factory function to create the Adviser Agent.
    """
    return Agent(
        name="Adviser",
        model=OpenAIChat(llm),
        tools=[
            DuckDuckGoTools(),
            SciResTool(),
            GoogleSearchTools(),
            HackerNewsTools(),
        ],
        add_history_to_messages=True,
        num_history_responses=3,
        description=dedent(description),
        instructions=dedent(instructions),
        markdown=False,
        memory=memory,
        user_id=agent_id(user_id, role="adviser"),
    )


# === Researcher Agent Factory ===
def make_researcher(
    llm, memory, agent_id, user_id, subtopic_index, researcher_instructions
):
    """
    Factory function to create a Researcher Agent for a given subtopic.
    """
    return Agent(
        name=f"Researcher {subtopic_index + 1}",
        model=OpenAIChat(llm),
        role="Research academic papers and scholarly content",
        add_history_to_messages=True,
        num_history_responses=3,
        tools=[
            GoogleSearchTools(),
            ArxivTools(),
            PhilippinesSearchTool(),
            SciResTool(),
        ],
        add_name_to_instructions=True,
        instructions=researcher_instructions.format(subtopic_index=subtopic_index),
        markdown=True,
        memory=memory,
        add_references=True,
        read_chat_history=True,
        user_id=agent_id(user_id, role=f"researcher_{subtopic_index}"),
    )


# === Supervisor Agent ===
def create_supervisor_agent(
    llm, memory, agent_id, user_id, description, instructions, role="supervisor"
):
    """
    Factory function to create a Supervisor Agent.
    """
    return Agent(
        name="Supervisor" if role == "supervisor" else "Supervisor 2",
        model=OpenAIChat(llm),
        add_history_to_messages=True,
        num_history_responses=3,
        description=dedent(description),
        instructions=dedent(instructions),
        markdown=True,
        memory=memory,
        user_id=agent_id(user_id, role=role),
    )


# === Citation Agent ===
def create_citation_agent(llm, memory, agent_id, user_id, description, instructions):
    """
    Factory function to create the Citation Agent.
    """
    return Agent(
        name="Citation Agent",
        model=OpenAIChat(llm),
        add_history_to_messages=True,
        num_history_responses=3,
        description=dedent(description),
        instructions=dedent(instructions),
        markdown=True,
        memory=memory,
        user_id=agent_id(user_id, role="citation_agent"),
    )
