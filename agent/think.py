import json
import time
from textwrap import dedent
from typing import List, Literal

from agno.agent import Agent
from agno.models.google import Gemini
from pydantic import BaseModel, Field

from agent.settings import GEMINI_MODEL_ID
from lib.utils import fetch_content_as_md, output_content, send_mail

question_history: List[str] = []
thinking_history: List[str] = []

modes = {
    "critical": {
        "reader": dedent("""\
            You're a reader with great insight and critical thinking.
            You will be given an article, the question history and answer history.
            You must ask 5 questions based on the given information, remember don't repeat the same or similar questions.
            each question should be clear and concise.
            output questions only, no explanation or unnecessary information.\
            """),
        "writer": dedent("""\
            You're the writer of a given article.
            You are responsible for answering the questions about your article.
            You must be objective and support your answers with evidence.
            Try to understand why the questions are being asked.
            If you find the questions are helpful to fix your article, then you're on the right track.
            """),
    },
    "faq": {
        "reader": dedent("""\
            You're a reader trying to understand the aticle and learn more about it.
            At the same time, you will be given the question history and answer history.
            You must ask 5 questions based on the given information, remember don't repeat the same or similar questions.
            each question should be clear and concise.
            output questions only, no explanation or unnecessary information.\
            """),
        "writer": dedent("""\
            You're the writer of a given article.
            You are responsible for answering the questions about your article.
            Try to help the reader understand the article better.\
            """),
    },
    # "creative": {},
    # "strategic": {},
}


class Config(BaseModel):
    mode: Literal["critical", "faq"] = Field(
        default=["critical"], description="thinking mode"
    )
    loops: int = Field(default=5, description="Loops for the thinking")
    lang: str = Field(default="english", description="Language for the report")
    receivers: List[str] | None = Field(
        default=None, description="List of email receivers"
    )
    format: Literal["md", "pdf"] = Field(
        default="md", description="Output format of the report"
    )


def ask_questions(article: str, config: Config, max_length: int) -> str:
    reader = Agent(
        name="Reader Agent",
        model=Gemini(id=GEMINI_MODEL_ID),
        description=modes[config.mode]["reader"],
        instructions=[
            f"the whole content should be less than {max_length} characters.",
            f"the output language: {config.lang}.",
        ],
        markdown=True,
    )
    prompt: str = (
        f"Article:\n{article}\nAsked Questions:\n{question_history}\nAnswers to Questions:\n{thinking_history}"
        if question_history
        else f"Article:\n{article}"
    )
    questions = reader.run(prompt).content
    question_history.append(questions)
    return questions


def answer_questions(
    article: str, question: str, config: Config, max_length: int
) -> str:
    writer = Agent(
        name="writer Agent",
        model=Gemini(id=GEMINI_MODEL_ID),
        description=modes[config.mode]["writer"],
        instructions=[
            f"the whole content should be less than {max_length} characters.",
            f"the output language: {config.lang}.",
        ],
        markdown=True,
    )
    prompt: str = f"Article:\n{article}\nQuestions:\n{question}"
    answers = writer.run(prompt).content
    thinking_history.append(answers)
    return answers


def output_thinking(link: str, config: Config) -> str:
    body = "\n".join(
        [
            f"## Question:\n\n {question}\n\n## Answer: \n\n{answer}"
            for question, answer in zip(question_history, thinking_history)
        ]
    )
    return f"# Thinking(Mode: {config.mode}) on {link}\n\n{body}"


def load_config(config: str | None) -> Config:
    if config is None:
        return Config()
    with open(config, "r") as file:
        json_data = json.load(file)
    return Config.model_validate(json_data)


def deep_think(link: str, config: str | None):
    c = load_config(config)
    article = fetch_content_as_md(link)
    if not article:
        print(f"Failed to fetch the content from {link}, exiting.")
        return

    for i in range(c.loops):
        print(f"Thinking Loop {i + 1} ---------------->")
        questions = ask_questions(article, c, 300)
        if not questions:
            print("No more questions, exiting.")
            break

        answers = answer_questions(article, questions, c, 600)

    print("Outputing ------------------>")
    if not questions or not answers:
        print("No questions or answers to output, exiting.")
        return

    content = output_thinking(link, c)
    topic = f"{c.mode}{int(time.time())}"
    output_content(topic, c.format, content)
    if c.receivers:
        send_mail(topic, c.receivers, content)
