import re

import fitz
from agno.agent import Agent, RunResponse
from agno.models.google import Gemini

mindmapPrompt = """
        Based on the given article:
        1. try to summary and extra the key points for the diagram generation.
        2. these key points must be informative and concise.
        3. these key points should highlight the author's viewpoints.
        4. try to keep the key points in a logical order.
        5. don't include any extra explanation and irrelevant information.

        Use them to generate a Mindmap.
        Mindmap syntax rules:
        - Each line should not have any quotes marks
        - Do not include 'mermaid' at the start of the diagram
        - Do not use 3-nesting parentheses for root, ie: "root((Mixture of Experts (MoE)))". The correct is "root((MoE))"
        - Do not use abbreviations with parentheses in the middle of a line, but it can be used at the end of a line
        - Do not use any special characters in the diagram except emojis
        - Keep function name without parameters when you are reading a programming article, ie: free, not free()
        - Can only have one root node, ie no other node can be at the same level as the root node.
        - Basic structure example:
        <Basic Structure>
        mindmap
          Root
            A
              B
              C

        Each node in the mindmap can be different shapes:
        <Square>
        id[I am a square]
        <Rounded square>
        id(I am a rounded square)
        <Circle>
        id((I am a circle))
        <Bang>
        id))I am a bang((
        <Cloud>
        id)I am a cloud(
        <Hexagon>
        id{{I am a hexagon}}
        <Default>
        I am the default shape

        Icons can be used in the mindmap with syntax: "::icon()"

        Markdown string can be used like the following:
        <Markdown string>
        mindmap
            id1["`**Root** with
        a second line
        Unicode works too: 🤓`"]
              id2["`The dog in **the** hog... a *very long text* that wraps to a new line`"]
              id3[Regular labels still works]

        Here is a mindmap example:
        <example mindmap>
        mindmap
          root((mindmap))
            Origins
              Long history
              ::icon(fa fa-book)
              Popularisation
                British popular psychology author Tony Buzan
            Research
              On effectiveness<br/>and features
              On Automatic creation
                Uses
                    Creative techniques
                    Strategic planning
                    Argument mapping
            Tools
              Pen and paper
              Mermaid

        The max deepth of the generated mindmap should be 4.

        The output syntax should be correct. Try to avoid the following common errors:
        - never use " in the output
        - ```mermaid in the output
        <error examples>
        - Gating network (G) decides experts (E)
          - fixed: Gating network decides experts
        - root((Mixture of Experts (MoE)))
          - fixed: root((MoE))
        - 2017: Shazeer et al. (Google) - 137B LSTM
          - fixed: 2017: Shazeer et al. Google 137B LSTM
        - calloc()
          - fixed: calloc
        - sbrk(0) returns current break
          - fixed: sbrk:0 returns current break
        - Allocate N + sizeof(header_t) bytes
          - fixed: Allocate N + sizeof header_t bytes

        Review the output to ensure it is logical and follows the correct syntax, if not, correct it.
    """

mind_agent = Agent(
    name="Decompose Agent",
    model=Gemini(id="gemini-2.0-flash-exp"),
    description="You are an MermaidJS diagram generator. You can generate stunning MermaidJS diagram codes.",
    instructions=mindmapPrompt,
    markdown=False,
)


def generate_summary(file: str, type: str):
    if type == "mindmap":
        _generate_mindmap(file)
    else:
        print(f"Summary type {type} not supported.")


def _generate_mindmap(file: str):
    doc = fitz.open(file)
    text = ""
    for page in doc:
        text += page.get_text()
    result: RunResponse = mind_agent.run(text)
    print("raw:\n", result.content)
    cleaned_result = _clean_text(result.content)
    print("cleaned:\n", cleaned_result)


def _clean_text(text: str):
    pattern = r"\s*\([^()]*?\)\s*(?![)])"
    text = re.sub(pattern, " ", text)
    return text
