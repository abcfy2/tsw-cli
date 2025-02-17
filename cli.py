import sys
from enum import Enum

import typer
from dotenv import load_dotenv

from agent.kb import generate_kb_entry, remove_kb_entry
from agent.research import start_research
from agent.summary import generate_summary

load_dotenv()

app = typer.Typer(help="a command line interface for your tiny smart workers.")
kb_app = typer.Typer(help="Commands related to the knowledge base.")


@app.command()
def research(
    topic: str = typer.Argument(..., help="report topic"),
    config: str | None = typer.Option(None, help="config file path"),
):
    """
    Generate a deep research report for a given topic.
    """
    start_research(topic, config)


class SummaryType(str, Enum):
    mindmap = "mindmap"
    text = "text"
    both = "both"


@app.command()
def summary(
    file: str = typer.Argument(..., help="File to generate a summary for"),
    type: SummaryType = typer.Option("mindmap", help="Summary type to generate"),
):
    """
    Generate a summary for a given file.
    """
    generate_summary(file, type)


@kb_app.command()
def create(
    file: str = typer.Argument(..., help="File for KB entry"),
    config: str = typer.Option(None, help="config file path"),
):
    """
    Create a new knowledge base entry.
    """
    generate_kb_entry(file, config)


@kb_app.command()
def refresh(
    file: str = typer.Argument(..., help="File for KB entry"),
    config: str = typer.Option(None, help="config file path"),
):
    """
    Create a new knowledge base entry.
    """
    generate_kb_entry(file, config, True)


@kb_app.command()
def remove(
    file: str = typer.Argument(..., help="File for KB entry"),
    config: str = typer.Option(None, help="config file path"),
):
    """
    Delete a knowledge base entry.
    """
    remove_kb_entry(file, config)


@app.command()
def kb():
    """
    Generate a knowledge base.
    """
    typer.echo("Knowledge Base")


app.add_typer(kb_app, name="kb")


def main():
    if len(sys.argv) == 1:
        sys.argv.append("--help")
    app()


if __name__ == "__main__":
    main()
