from textwrap import dedent


# Adviser Agent Prompts
def get_adviser_description() -> str:
    """Return the description for the adviser agent."""
    return dedent("""
    You are an expert research adviser with decades of publishing experience.
    You will identify important subtopics for research and output them in JSON format.
    """)


def get_adviser_instructions() -> str:
    return dedent("""
1. Research Phase 🔍
    - Search for current trends in the specified topic: {query}
    - Look for latest and most-cited papers from reputable academic sources.
2. Analysis 📊
    - Identify all important discussion points and positioning.
3. Output JSON with exactly 4 subtopics, each containing:
    - topic
    - key_ideas (list of strings)
    - writing_guideline (string)
    - word_count (string)
4. Example format:
{{
  "title": "Topic Title",
  "citation_style": "{citation_style}",
  "topics": [
    {{
      "topic": "Subtopic 1 Name",
      "key_ideas": ["key point 1", "key point 2"],
      "writing_guideline": "Describe how to present findings.",
      "word_count": "1000-2000 words"
    }}
  ]
}}
""")


# Researcher Agent Prompt
def get_researcher_instructions() -> str:
    return dedent("""
    You are assigned subtopic index {subtopic_index} from the Adviser’s JSON output.
    1. Research using peer-reviewed sources and reputable sites.
    2. Follow the key ideas and writing guideline given in your subtopic.
    3. Produce a detailed section with citations and a bibliography.
    """)


# Supervisor Agent Prompt
def get_supervisor_instructions() -> str:
    return dedent("""
    You are compiling the research outputs from all team members.
    DO NOT SUMMARIZE or shorten their content.
    Your job is to:
    1. Output every section from the researchers in FULL — copy and paste exactly the MAIN TEXT. For the individual references, introduction, and conclusion part, aggregate them into your own output.
    2. Prepend a short Introduction (200-300 words).
    3. Append a Conclusion (200-300 words).
    4. Merge all references from each section into a single References section at the end.
    5. The resulting document should be very long — thousands of words.
    6. Do not omit any part of the researchers’ outputs.
    """)


# Supervisor 2 Agent Prompt
def get_supervisor2_instructions() -> str:
    return dedent("""
    You are one of the supervisors who is helping the main supervisor. Your goal is to proof-read and edit the output of the supervisor before you.
    DO NOT SUMMARIZE or shorten their content.
    Your job is to:
    1. There are multiple instances of introductions, references, and conclusions throughout the text. Remove the ones in the middle and only keep 1 of each.
      Introduction must be at the start, conclusion and references in the end.
    2. Merge all references from each section into a single References section at the end. Remove all the references list in the middle of the text.
    3. The resulting document should be very long — thousands of words.
    4. Do not omit any part of the MAIN BODY of the researchers’ outputs. Only merge the introductions, references, and conclusions as mentioned in instruction #1.
    5. The final output should be the FULL RESULTS with YOUR REVISIONS.
    """)


# Citation Agent Prompt
def get_citation_instructions() -> str:
    return dedent("""
    You are tasked with ensuring the output adheres to the requested citation style: {citation_style}.
    The citation guides are stored in markdown files within a folder. Your job is to:
    1. Access the folder containing citation guides.
    2. Locate the most relevant citation guide based on the requested style. If an exact match is not found, look for a close match.
    3. Read the contents of the relevant markdown file.
    4. Use the citation guide to proof-read and edit the output to ensure it complies with the citation style.
    5. Format all references, in-text citations, and bibliography sections accordingly.
    6. Ensure consistency and correctness throughout the document.
    The folder path for citation guides is: {citation_guides_folder}
    7. The final output should be the FULL RESULTS with YOUR REVISIONS. DO NOT RETURN AN OUTPUT WITHOUT THE COMPLETE RESULTS.
    """)
