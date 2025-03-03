from agent.kb import list_kb_entries
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My-KB")

config = "/Users/hujian/projects/creative/tsw-cli/config/kb.json"


@mcp.resource("tsw://kb")
def get_entry() -> str:
    return list_kb_entries(config)
