import sys
from enum import Enum

import typer
from dotenv import load_dotenv

from agent.report import generate_report
from agent.summary import generate_summary

load_dotenv()

app = typer.Typer(help="a command line interface for your tiny smart workers.")


@app.command()
def report(
    topic: str = typer.Argument(..., help="report topic"),
    config: str | None = typer.Option(None, help="config file path"),
):
    """
    Generate a report for a given topic.
    """
    generate_report(topic, config)


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


def main():
    if len(sys.argv) == 1:
        sys.argv.append("--help")
    app()


if __name__ == "__main__":
    main()
