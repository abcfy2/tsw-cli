# Reference: https://github.com/dzhng/deep-research

import json
import time
from textwrap import dedent
from typing import List, Literal

from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.groq import Groq
from agno.tools.googlesearch import GoogleSearch
from pydantic import BaseModel, Field

from agent.settings import GEMINI_MODEL_ID, GROQ_MODEL_ID
from lib.utils import output_content, send_mail

thinkings: List[str] = []


class Config(BaseModel):
    deepth: int = Field(default=2, description="Deepth of the research")
    breadth: int = Field(default=3, description="Breadth of the research")
    lang: str = Field(default="english", description="Language for the report")
    receivers: List[str] | None = Field(
        default=None, description="List of email receivers"
    )
    format: Literal["md", "pdf"] = Field(
        default="md", description="Output format of the report"
    )


class SubItems(BaseModel):
    items: List[str]


def ask_questions(query: str, n: int) -> SubItems:
    question_agent = Agent(
        name="Question Agent",
        model=Groq(id=GROQ_MODEL_ID),
        description="You're a great questioner with critical thinking skills.",
        instructions=[
            "generate a list of questions based on the given query.",
            f"the number of questions should be less than or equal to {n}.",
        ],
        show_tool_calls=True,
        response_model=SubItems,
    )
    return question_agent.run(query).content


def generate_subqueries(query: str, questions: SubItems) -> List[str]:
    query_agent = Agent(
        name="Query Agent",
        model=Groq(id=GROQ_MODEL_ID),
        description="You're a great agent with excellent search query generation skills.",
        instructions=[
            f"generate a list of subqueries based on {query} and questions.",
            "the number of questions should be less than or equal to 3.",
            "it's okay to generate an empty list.",
        ],
        show_tool_calls=True,
        response_model=SubItems,
    )
    subqueries = []
    for question in questions.items:
        query_result = query_agent.run(question).content
        subqueries.extend(query_result.items)
    return subqueries


search_agent = Agent(
    name="Search Agent",
    model=Groq(id=GROQ_MODEL_ID),
    tools=[GoogleSearch(fixed_max_results=10)],
    description="You're a good searcher with excellent information gathering skills.",
    instructions=[
        "try your best to search the given query and gather information.",
    ],
    show_tool_calls=True,
)

mid_report_agent = Agent(
    name="Mid Report Agent",
    model=Gemini(id=GEMINI_MODEL_ID),
    description="You're a great agent with excellent information synthesis skills.",
    instructions=[
        "first, gather all the information from the search results.",
        "then, group them by subtopics.",
        "finally, generate a mid report based on the information.",
    ],
)


def create_analysis_agent(lang: str) -> Agent:
    return Agent(
        name="Analysis Agent",
        model=Gemini(id=GEMINI_MODEL_ID),
        description=dedent("""\
            You are an expert researcher. Follow these instructions when responding:
            - You may be asked to research subjects that is after your knowledge cutoff, assume the user is right when presented with news.
            - The user is a highly experienced analyst, no need to simplify it, be as detailed as possible and make sure your response is correct.
            - Be highly organized.
            - Suggest solutions that I didn't think about.
            - Be proactive and anticipate my needs.
            - Treat me as an expert in all subject matter.
            - Mistakes erode my trust, so be accurate and thorough.
            - Provide detailed explanations, I'm comfortable with lots of detail.
            - Value good arguments over authorities, the source is irrelevant.
            - Consider new technologies and contrarian ideas, not just the conventional wisdom.
            - You may use high levels of speculation or prediction, just flag it for me.\
        """),
        instructions=[
            "You're known for your ability to turn complex data into clear and concise reports, making it easy for others to understand and act on the information you provide."
            "Generate a report based on the research results.",
            "Always include sources as a reference in the report",
            "The report should be informative with a clear structure and easy to understand.",
            "At the same time, the report should include a summary of the most important findings and insights.",
            "Output the report without any additional explanation or commentary.",
            f"Write the report in language: {lang}.",
        ],
        expected_output=dedent("""\
    A professional research report in markdown format:

    # {Compelling Title That Captures the Topic's Essence}

    ## Summary
    {Brief overview of key findings and significance}

    ## Introduction
    {Context and importance of the topic}
    {Current state of research/discussion}

    ## {Subtopic}
    {Major discoveries or developments}
    {Supporting evidence and analysis}

    ## Key Takeaways
    - {Bullet point 1}
    - {Bullet point 2}
    - {Bullet point 3}

    ## References
    - [Source 1](link) - Key finding/quote
    - [Source 2](link) - Key finding/quote
    - [Source 3](link) - Key finding/quote

    ---
    Report generated by TSW-X
    Advanced Research Systems Division
    Date: {current_date}\
    """),
        show_tool_calls=True,
        markdown=True,
        add_datetime_to_instructions=True,
    )


def load_config(config: str | None) -> Config:
    if config is None:
        return Config()
    with open(config, "r") as file:
        json_data = json.load(file)
    return Config.model_validate(json_data)


def start_research(topic: str, config: str | None):
    c = load_config(config)
    for i in range(c.deepth):
        questions = ask_questions(topic, c.breadth)
        print(
            f"--------------questions--------------:\n{questions}\n--------------questions--------------"
        )
        subqueries = generate_subqueries(topic, questions)
        research_result = []
        for subquery in subqueries:
            print("searching for:", subquery)
            research_result.append(search_agent.run(subquery).content)
            time.sleep(5)
        mid_report_result = mid_report_agent.run("\n".join(research_result))
        thinkings.append(mid_report_result.content)
        time.sleep(5)
    print("--------------generating final report--------------")
    analysisResult = create_analysis_agent(c.lang).run("\n".join(thinkings))
    output_content(topic, c.format, analysisResult.content)
    if c.receivers:
        send_mail(topic, c.receivers, analysisResult.content)  # noqa: F821
