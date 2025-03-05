import sys
from enum import Enum

import typer
from dotenv import load_dotenv

from agent.code import explain_repo
from agent.kb import generate_kb_entry, list_kb_entries, remove_kb_entry
from agent.research import start_research
from agent.summary import generate_summary
from agent.think import deep_think
from agent.writer import write_article

load_dotenv()

app = typer.Typer(help="a command line interface for your tiny smart workers.")
kb_app = typer.Typer(help="Commands related to the knowledge base.")
code_app = typer.Typer(help="Commands related to the coding.")


@app.command()
def research(
    config: str = typer.Argument(..., help="config file path"),
):
    """
    Generate a deep research report for a given topic.
    """
    start_research(config)


@app.command()
def think(
    config: str = typer.Argument(..., help="config file path"),
):
    """
    Deeply think about a given link.
    """
    deep_think(config)


@app.command()
def write(
    config: str = typer.Argument(None, help="config file path"),
):
    """
    Write a new article.
    """
    write_article(config)


class SummaryType(str, Enum):
    mindmap = "mindmap"
    text = "text"
    both = "both"


@app.command()
def summarise(
    file: str = typer.Argument(..., help="File to generate a summary for"),
    type: SummaryType = typer.Option("mindmap", help="Summary type to generate"),
):
    """
    Generate a summary for a given file.
    """
    generate_summary(file, type)


@kb_app.command()
def list(
    config: str = typer.Argument(None, help="config file path"),
):
    """
    List all knowledge base entries
    """
    list_kb_entries(config)


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
    name: str = typer.Argument(..., help="name for KB entry"),
    config: str = typer.Option(None, help="config file path"),
):
    """
    Delete a knowledge base entry.
    """
    remove_kb_entry(name, config)


@code_app.command()
def explain(
    config: str = typer.Argument(..., help="config file path"),
):
    """
    Explain a given code repo.
    """
    explain_repo(config)


app.add_typer(kb_app, name="kb")
app.add_typer(code_app, name="code")


def main():
    if len(sys.argv) == 1:
        sys.argv.append("--help")
    elif len(sys.argv) == 2 and sys.argv[1] in ["kb", "code"]:
        sys.argv.append("--help")
    app()


if __name__ == "__main__":
    main()
