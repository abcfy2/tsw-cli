import time
from typing import List

from agno.agent import Agent, RunResponse
from agno.models.google import Gemini
from agno.tools.duckduckgo import DuckDuckGoTools
from dotenv import load_dotenv
from pydantic import BaseModel

from lib.utils import pdf_report

load_dotenv()


class SubTopics(BaseModel):
    names: List[str]


decompose_agent = Agent(
    name="Decompose Agent",
    model=Gemini(id="gemini-2.0-flash-exp"),
    description="You're a skilled decomposer with a talent for breaking down complex topics into digestible parts.",
    instructions=[
        "Thinking of a topic, break it down into its key components.",
        "return a list of the key components of the topic.",
        "the list should be ordered by importance.",
        "return a maximum of 5 subtopics.",
    ],
    show_tool_calls=True,
    markdown=True,
    response_model=SubTopics,
)


research_agent = Agent(
    name="Research Agent",
    model=Gemini(id="gemini-2.0-flash-exp"),
    tools=[DuckDuckGoTools(fixed_max_results=10)],
    description="You're a seasoned researcher with a knack for uncovering the latest developments in a given topic.",
    instructions=[
        "Known for your ability to find the most relevant information and present it in a clear and concise manner.",
        "Always include links in the output",
    ],
    show_tool_calls=True,
    markdown=True,
)


analysis_agent = Agent(
    name="Analysis Agent",
    model=Gemini(id="gemini-2.0-flash-exp"),
    description="You're a meticulous analyst with a keen eye for detail.",
    instructions=[
        "You're known for your ability to turn complex data into clear and concise reports, making it easy for others to understand and act on the information you provide."
        "Generate a report based on the research results.",
        "Always include sources as a reference in the report",
        "The report should be informative with a clear structure and easy to understand.",
        "At the same time, the report should include a summary of the most important findings and insights.",
        "Output the report without any additional explanation or commentary.",
    ],
    show_tool_calls=True,
    markdown=True,
)


def research(topic: str) -> str:
    result: RunResponse = decompose_agent.run(topic)
    subTopics = result.content
    research = []
    for sub_topic in subTopics:
        research.append(
            research_agent.run(
                f"What are the latest developments in {sub_topic}"
            ).content
        )
        # rate limiting
        time.sleep(0.5)
    return "\n".join(research)


def generate_report(topic: str):
    researchResult = research(topic)
    analysisResult: RunResponse = analysis_agent.run(researchResult)
    pdf_report(topic, analysisResult.content)
