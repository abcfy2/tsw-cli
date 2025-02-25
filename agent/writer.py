import json
import time
from textwrap import dedent
from typing import List, Literal

from agno.agent import Agent
from agno.models.google import Gemini
from pydantic import BaseModel, Field

from agent.settings import GEMINI_MODEL_ID
from lib.utils import output_content, read, search_topic

MAX_REVISIONS = 5

reference_history = []
expected_output = dedent("""\
    A professional technical article in markdown format:

    # {Compelling Title That Captures the Topic's Essence}

    ## Tags
    {tags}
    
    {the body of the article in multiple sections}

    ## References
    {List of sources, citations, and links}
    \
    """)


class Config(BaseModel):
    agenda: str = Field(description="A file path to the agenda")
    tags: List[str] = Field(default=[], description="List of tags for the research")
    lang: str = Field(default="english", description="Language for the article")
    tranlations: List[str] = Field(
        default=["chinese"], description="List of languages for translation"
    )
    revisions: int = Field(
        default=3, le=MAX_REVISIONS, description="Number of revisions"
    )
    reviewers: List[str] | None = Field(
        default=None, description="List of human reviewers for the article"
    )
    format: Literal["md", "pdf"] = Field(
        default="md", description="Output format of the article"
    )


def write_draft(agenda: str, tags: List[str] = []) -> str:
    results = search_topic(",".join(tags), 3, reference_history)
    reference_history.extend(results["links"])
    writer = Agent(
        name="Writer Agent",
        model=Gemini(id=GEMINI_MODEL_ID),
        description="You are a professional technical writer and an expert in the field.",
        instructions=[
            "you will be given an agenda and some references documents to write a technical article.",
            "your readers are technical experts, so the article should be detailed and informative.",
            "you can use the references to write the article, but don't copy-paste.",
            "the final article should be less than 3000 characters",
        ],
        expected_output=expected_output,
        markdown=True,
    )
    return writer.run(
        f"Agenda:\n{agenda}\nTags:\n{','.join(tags)}\nReference Document:\n{results['articles']}\nReferences Links:\n{reference_history}"
    ).content


def revise_draft(draft: str, feedback: str) -> str:
    writer = Agent(
        name="Writer Agent",
        model=Gemini(id=GEMINI_MODEL_ID),
        description="You are a professional technical writer and an expert in the field.",
        instructions=[
            "your article has been reviewed and you have received feedback.",
            "revise the article based on the feedback.",
        ],
        expected_output=expected_output,
        markdown=True,
    )
    return writer.run(f"Draft:\n{draft}\nFeedback:\n{feedback}").content


def review_draft(draft: str) -> str:
    editor = Agent(
        name="Editor Agent",
        model=Gemini(id=GEMINI_MODEL_ID),
        description="You are a professional technical editor.",
        instructions=[
            "given a draft of an article, read it and give feedback to improve its quality, readability and accuracy.",
            "only return your feedback, no other information or explanation.",
            "the feedback should be less than 200 characters",
        ],
        markdown=True,
    )
    return editor.run(draft).content


def load_config(config: str | None) -> Config:
    if config is None:
        return Config()
    with open(config, "r") as file:
        json_data = json.load(file)
    return Config.model_validate(json_data)


def write_article(config: str):
    c = load_config(config)
    agenda = read(c.agenda)
    print("Writing Draft ------------------>")
    draft = write_draft(agenda, c.tags)
    for i in range(c.revisions):
        print(f"Reviewing Draft: {i + 1} ------------------>")
        feedback = review_draft(draft)
        if not feedback:
            print("No feedback received. Article is ready.")
            break
        draft = revise_draft(draft, feedback)
    print("Saving ------------------>")
    topic = f"article{int(time.time())}"
    output_content(topic, c.format, draft)
    # if c.receivers:
    #     send_mail(topic, c.receivers, draft)
