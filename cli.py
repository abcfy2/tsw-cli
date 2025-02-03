import sys

import typer

from agent.topic_report import generate_report

app = typer.Typer(help="a command line interface for your tiny smart workers.")


@app.command()
def report(
    topic: str = typer.Argument(..., help="topic to generate a report for"),
):
    """
    Generate a report for a given topic.
    """
    generate_report(topic)


def main():
    if len(sys.argv) == 1:
        sys.argv.append("--help")
    app()


if __name__ == "__main__":
    main()
