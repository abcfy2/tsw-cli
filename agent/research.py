# Reference: https://github.com/dzhng/deep-research

import json
import time
from textwrap import dedent
from typing import List, Literal

from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.googlesearch import GoogleSearch
from pydantic import BaseModel, Field

from agent.settings import GEMINI_MODEL_ID
from lib.utils import output_content, send_mail

thinkings: List[str] = []
asked_questions: List[str] = []


class Config(BaseModel):
    deepth: int = Field(default=3, description="Deepth of the research")
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


def ask_questions(query: str, n: int) -> List[str]:
    question_agent = Agent(
        name="Question Agent",
        model=Gemini(id=GEMINI_MODEL_ID),
        description="You're a great questioner with critical thinking skills.",
        instructions=[
            "generate a list of questions based on the given query.",
            "never ask old or similar questions, be creative.",
            f"the maximum number of questions must be {n}.",
            "it's okay to generate an empty list.",
        ],
        show_tool_calls=True,
        response_model=SubItems,
    )
    if asked_questions:
        old_questions = ",".join(asked_questions)
        result = question_agent.run(
            f"Query:\n {query},\n asked questions:\n [{old_questions}]"
        )
    else:
        result = question_agent.run(query)
    items = result.content.items
    if len(items) > n:
        items = items[:n]
    return items


def generate_query(query: str, questions: List[str]) -> List[str]:
    query_agent = Agent(
        name="Query Agent",
        model=Gemini(id=GEMINI_MODEL_ID),
        description="You're a great agent with excellent search query generation skills.",
        instructions=[
            f"generate a line of keywords for google search based on {query} and the given question.",
            "return keywords only, no explanation and other information.",
        ],
        show_tool_calls=True,
    )
    query_keywords = []
    for question in questions:
        query_keywords.append(query_agent.run(question).content)
        time.sleep(2)
    return query_keywords


search_agent = Agent(
    name="Search Agent",
    model=Gemini(id=GEMINI_MODEL_ID),
    tools=[GoogleSearch(fixed_max_results=5)],
    description="You're a good searcher with excellent information gathering skills.",
    instructions=[
        "try your best to search the given query and gather information.",
        "if you can't find a tool, ignore it.",
        "always include the source citation and its link in the gathered information.",
    ],
    show_tool_calls=True,
)

mid_report_agent = Agent(
    name="Mid Report Agent",
    model=Gemini(id=GEMINI_MODEL_ID),
    description="You're a great agent with excellent information synthesis skills.",
    instructions=[
        "generate a mid report for a given topic based on the gathered information.",
        "first, understand the information and generate thinkings.",
        "then, group them by subtopics.",
        "finally, generate a mid report based on the information.",
        "when the report is done, review it and try to make it related to the topic.",
        "keep all the links and citations in the report.",
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
            "generate a professional research report based on the given thinking and topic.",
            "you can ignore those unrelated information.",
            "but don't miss any related information even if it's not directly asked.",
            f"Write the report in language: {lang}.",
        ],
        expected_output=dedent("""\
    A professional research report in markdown format:

    # {Compelling Title That Captures the Topic's Essence}

    ## Summary
    {Brief overview of key findings and significance}
    
    ## Introduction
    {A brief introduction to the topic and the purpose of the report}
    {Background information on the topic and explain how the research was conducted}

    <Subtopics>
    ## Subtopic
    {Key findings and analysis on the subtopic}
    
    ### Suggested Actions
    {Possible actions or recommendations}
    {Risks and challenges}
    </Subtopics>

    ## Insights
    {Key insights and conclusions from the research}

    ## Conclusion
    {Summary of the generated content}
    {Highlight the key takeaways}

    ## References
    {List of sources, citations, and links}

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
    research_topics = [topic]
    for i in range(c.deepth):
        for research_topic in research_topics:
            print(f"--------------researching on {research_topic}--------------")
            questions = ask_questions(research_topic, c.breadth)
            asked_questions.extend(questions)
            research_topics = questions
            print(
                f"--------------questions--------------:\n{questions}\n--------------questions--------------"
            )
            subqueries = generate_query(topic, questions)
            research_result = []
            for subquery in subqueries:
                print("searching for:", subquery)
                try:
                    research_result.append(search_agent.run(subquery).content)
                except Exception as e:
                    print("search failed, ignore:", e)
                time.sleep(5)
            gathered_information = "\n".join(research_result)
            thinkings.append(
                mid_report_agent.run(
                    f"topic:\n{topic}\ngathered information:\n{gathered_information}"
                ).content
            )
            time.sleep(5)
    print("--------------generating final report--------------")
    all_thinkings = "\n".join(thinkings)
    analysisResult = (
        create_analysis_agent(c.lang)
        .run(f"Topic: {topic}\n All Thinking: {all_thinkings}")
        .content
    )
    output_content(topic, c.format, analysisResult)
    if c.receivers:
        send_mail(topic, c.receivers, analysisResult)
