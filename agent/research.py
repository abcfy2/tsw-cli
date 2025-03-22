# Reference: https://github.com/dzhng/deep-research

import json
import time
from textwrap import dedent
from typing import List, Literal

from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.groq import Groq
from pydantic import BaseModel, Field

from agent.settings import GEMINI_MODEL_ID, GROQ_MODEL_ID
from lib.utils import get_block_body, output_content, search_topic, send_mail

learnings: List[str] = []
insights: List[str] = []
generated_queries: List[str] = []
references: List[str] = []

system_prompt = dedent("""\
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
""")


class Config(BaseModel):
    topic: str = Field(description="Research topic")
    hints: list[str] = Field(default=[], description="hints for the task")
    depth: int = Field(default=2, description="Depth of the research")
    breadth: int = Field(default=1, description="Breadth of the research")
    lang: str = Field(default="english", description="Language for the report")
    receivers: List[str] | None = Field(
        default=None, description="List of email receivers"
    )
    format: Literal["md", "pdf"] = Field(
        default="md", description="Output format of the report"
    )


def summary_learnings(topic: str, max_length: int):
    if not learnings:
        return ""

    print("-------summarizing learning-------------->")
    all_learnings = "\n".join(learnings)
    reader = Agent(
        name="Reader Agent",
        model=Gemini(id=GEMINI_MODEL_ID),
        description="you are an insightful reader and can extract the key points from the text.",
        instructions=[
            "extract the key points related to the topic from the given text.",
            "don't include the irrelevant information.",
            "don't miss any important points.",
            f"the maximum length of the summary is {max_length} characters.",
        ],
    )
    insights.append(reader.run(f"Topic:\n{topic}\nLearnings:\n{all_learnings}").content)
    learnings.clear()


def plan_research(topic: str, hints: List[str] = []) -> str:
    planner = Agent(
        name="Planner Agent",
        model=Groq(id=GROQ_MODEL_ID, temperature=0),
        description=system_prompt,
        instructions=[
            "you will be given a research topic and some hints, generate a google search query based on them.",
            "you will also be given the history of previous queries and what you have learnt.",
            "don't repeat the same or similar queries, try to generate new ones.",
            "use what you have learnt to inspire you to generate new queries.",
            "the generated query should be relevant to the topic and the hints, it can be creative but shouldn't be off-topic.",
            "the generated query should be several keywords for a google search.",
            "only return the generated query, no other information or explanation.",
        ],
    )
    try:
        goal: str = (
            f"Research Topic:\n{topic}\nWhat I have learnt:\n{','.join(insights)}"
            if insights
            else f"Research Topic:\n{topic}"
        )
        h: str = f"\nHints:\n{','.join(hints)}" if hints else ""
        history: str = (
            f"\nOld Query Keywords:\n{','.join(generated_queries)}"
            if generated_queries
            else ""
        )
        result = planner.run(f"{goal}{h}{history}").content
        generated_queries.append(result)
    except Exception as e:
        print(e)
        result = ""
    return result


def read_articles(topic: str, articles: List[str], max_length: int):
    analyst = Agent(
        name="Analyst Agent",
        model=Gemini(id=GEMINI_MODEL_ID),
        description=system_prompt,
        instructions=[
            "learn the information related to the research topic in the articles.",
            "include the citations which are relevant to the topic.",
            "ignore the unrelated information.",
            "generate a mid-report based on the gathered information.",
            f"the report should be clear and concise, the whole content should be less than {max_length} characters.",
        ],
        markdown=True,
    )
    for article in articles:
        print("---Reading article-------------->")
        learnings.append(analyst.run(f"Topic:\n{topic}\nArticles:\n{article}").content)
        time.sleep(5)


def write_final_report(topic: str, lang: str) -> str:
    researcher = Agent(
        name="Researcher Agent",
        model=Gemini(id=GEMINI_MODEL_ID, grounding=True),
        description=system_prompt,
        instructions=[
            "generate a professional research report based on the topic and what you have learnt.",
            "the report reader is an expert, so no need to simplify it.",
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
    return researcher.run(
        f"Topic:\n{topic}\nMy Learnings:\n{insights}\nReferences:\n{references}"
    ).content


def load_config(config: str) -> Config:
    with open(config, "r") as file:
        json_data = json.load(file)
    return Config.model_validate(json_data)


def start_research(config: str):
    c = load_config(config)
    topic = c.topic
    for i in range(c.depth):
        print(f"Researching Depth {i + 1} ---------------->")
        plan = plan_research(topic, c.hints)
        if not plan:
            print("No plan to search for, ignoring this depth.")
            continue
        print(f"Searching for: {plan}")
        results = search_topic(plan, c.breadth, references)
        references.extend(results["links"])
        read_articles(topic, results["articles"], 500)
        summary_learnings(topic, 250)
    print("Generating Final Report ------------------>")
    if not insights:
        print("No insights to generate a report, exiting.")
        return
    report = get_block_body(write_final_report(topic, c.lang))
    output_content(topic, c.format, report)
    if c.receivers:
        send_mail(topic, c.receivers, report)
