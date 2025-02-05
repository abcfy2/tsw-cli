import os

import fitz
from markdown_pdf import MarkdownPdf, Section

output_dir = "output"
os.makedirs(output_dir, exist_ok=True)


def generate_pdf(name: str, markdown: str) -> None:
    """
    Generates a PDF from the given markdown content.

    Args:
        name (str): pdf file name.
        markdown (str): The markdown content for the pdf.

    Returns:
        None
    """
    pdf = MarkdownPdf()
    pdf.add_section(Section(markdown))
    try:
        pdf.save(f"{output_dir}/{name}.pdf")
    except IOError as e:
        print(f"Failed to save PDF report: {e}")


def write(name: str, markdown: str, append=False) -> str:
    mode = "a" if append else "w"
    with open(f"{output_dir}/{name}.md", mode) as f:
        f.write(markdown)
    return


def extract_text_from_pdf(file):
    doc = fitz.open(file)
    text = ""
    for page in doc:
        text += page.get_text()
    return text
