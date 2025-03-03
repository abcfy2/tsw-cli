import re
from textwrap import dedent

from agno.agent import Agent, RunResponse
from agno.models.google import Gemini

from agent.settings import GEMINI_MODEL_ID
from lib.pako import generate_image_dataurl, generate_pako_link
from lib.utils import download, extract_text_from_pdf, filename, get_block_body, write

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

        The max depth of the generated mindmap should be 3.

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

mindmap_agent = Agent(
    name="Mindmap Agent",
    model=Gemini(id=GEMINI_MODEL_ID),
    description="You are an MermaidJS diagram generator. You can generate stunning MermaidJS diagram codes.",
    instructions=mindmapPrompt,
    markdown=False,
)

summary_agent = Agent(
    name="Summary Agent",
    model=Gemini(id=GEMINI_MODEL_ID),
    description="You are a good paper reader and need to explain what you have read to others.",
    instructions=[
        "1. find the main points of the document.",
        "2. for each main point, provide a informative summary and explain the implementation if needed.",
        "3. for each complex concept, provide a brief explanation.",
        "4. make the whole summary readable and engaging.",
    ],
    expected_output=dedent("""\
    A concise summary in markdown format:

    # {A Title That Captures the Essence of the Text}

    ## Summary
    {Brief overview of key findings and significance}

    ## Terminology
    - {Term 1}: {Definition}
    - {Term 2}: {Definition}

    ## Main Points
    ### Point 1
    {Main point 1}
    {Explanation or implementation}

    ### Point 2
    {Main point 2}
    {Explanation or implementation}

    ## Improvements And Creativity
    {Main improvements and creativity in the text}

    ## Insights
    {Your insights on the text}
    {Your predictions or recommendations}

    ## References
    - [Source 1](link) - Link in given text
    - [Source 2](link) - Link in given text
    - [Source 3](link) - Link in given text

    ---
    Report generated by TSW-X
    Advanced Research Systems Division
    Date: {current_date}\
    """),
    markdown=True,
    add_datetime_to_instructions=True,
)

summary_team = Agent(
    name="Summary Team",
    model=Gemini(id=GEMINI_MODEL_ID),
    team=[mindmap_agent, summary_agent],
    instructions=[
        "First, search hackernews for what the user is asking about.",
        "Then, ask the article reader to read the links for the stories to get more information.",
        "Important: you must provide the article reader with the links to read.",
        "Then, ask the web searcher to search for each story to get more information.",
        "Finally, provide a thoughtful and engaging summary.",
    ],
    show_tool_calls=True,
    markdown=True,
)


def generate_summary(file: str, type: str):
    if type == "mindmap":
        text = extract_text_from_pdf(file)
        link = _generate_mindmap(text)
        download(link, f"{filename(file)}.png")
    elif type == "text":
        text = extract_text_from_pdf(file)
        summary = _generate_text(text)
        write(f"{filename(file)}.md", summary)
    elif type == "both":
        text = extract_text_from_pdf(file)
        mindmap, summary = _generate_both(text)
        lines = summary.split("\n")
        lines.insert(1, f"\n## Mindmap\n![Mindmap]({generate_image_dataurl(mindmap)})")
        summary = "\n".join(lines)
        write(f"{filename(file)}.md", summary)
    else:
        print(f"Summary type {type} not supported.")


def _generate_mindmap(text: str) -> str:
    result: RunResponse = mindmap_agent.run(text)
    print("raw:\n", result.content)
    cleaned_result = _clean_text(result.content)
    print("cleaned:\n", cleaned_result)
    image_link = generate_pako_link(cleaned_result)
    print("visit link:\n", image_link)
    return image_link


def _generate_text(text: str) -> str:
    return get_block_body(summary_agent.run(text).content)


def _generate_both(text: str) -> tuple:
    mindmap = _generate_mindmap(text)
    summary = _generate_text(text)
    return mindmap, summary


def _clean_text(text: str):
    text = get_block_body(text)
    lines = []
    for line in text.split("\n"):
        if "root((" in line:
            pattern = r"(\(\([^()]*?)\s+\([^()]*?\)(.*?\)\))"

            def replacer(match):
                return f"{match.group(1)}{match.group(2)}"

            line = re.sub(pattern, replacer, line)
        else:
            pattern = r"\s*\([^()]*?\)\s*(?=:|\w|\s)"
            line = re.sub(pattern, "", line)
        lines.append(line)

    return "\n".join(lines)
