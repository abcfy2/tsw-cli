import os

from markdown_pdf import MarkdownPdf, Section


def pdf_report(topic: str, markdown: str) -> None:
    """
    Generates a PDF report from the given markdown content.

    Args:
        topic (str): The topic of the report, used as the filename.
        markdown (str): The markdown content to be converted to PDF.

    Returns:
        None
    """
    pdf = MarkdownPdf()
    pdf.add_section(Section(markdown))
    os.makedirs("reports", exist_ok=True)
    try:
        pdf.save(f"reports/{topic}.pdf")
    except IOError as e:
        print(f"Failed to save PDF report: {e}")
