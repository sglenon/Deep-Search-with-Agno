import json
import re
from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.arxiv import ArxivTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.googlesearch import GoogleSearchTools
from agno.tools.hackernews import HackerNewsTools
from gpt_researcher import GPTResearcher

from tools.philippines_search_tool import PhilippinesSearchTool
from tools.sci_paper_search_tool import SciResTool


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


# === Compiler pervisor Agent ===
def create_compiler_agent(
    llm, memory, agent_id, user_id, description, instructions, role="supervisor"
):
    """
    Factory function to create a Supervisor Agent.
    """
    return Agent(
        name="Compiler",
        model=OpenAIChat(llm),
        add_history_to_messages=True,
        num_history_responses=3,
        instructions=dedent(instructions),
        markdown=True,
        memory=memory,
        user_id=agent_id(user_id, role=role),
    )


# === Custom Functions ====
def extract_json_step(response_text: str):
    """
    This function just extracts the url links from the research agents.
    """
    matches = re.findall(r'\{[^{}]*"url_links"[^{}]*\}', response_text, re.DOTALL)
    all_links = []
    for match in matches:
        try:
            data = json.loads(match)
            urls = data.get("url_links", [])
            all_links.extend(urls)
        except json.JSONDecodeError:
            continue
    return {"url_links": list(set(all_links))}


async def get_report_step(inputs: dict):
    """
    This function runs GPTResearcher to create an output based on the URLs obtained by the previous function.
    """
    sources = inputs.get("url_links", [])
    query = inputs.get("query")
    researcher = GPTResearcher(
        query=query,
        report_type="research_report",
        source_urls=sources,
        complement_source_urls=False,
    )
    await researcher.conduct_research()
    report = await researcher.write_report()
    return {"report": report, "url_links": sources}
