# tsw-cli

A command line interface for your tiny smart workers.

## How to Run

1. configure your environment
1. `uv sync`
1. `source .venv/bin/activate`
1. `uv pip install .`
1. `tsw-cli --help`
1. `tsw-cli --config <your_config_file>`

Note:

- for environment configuration, you can use the `.env.example` file
- normally, each command has a `--config` option to specify the configuration file. for its details, you can find them in codes.
- the default PG schema for Knowledge is `ai`, you can find it with `\dn` in psql.

## MCP Server

prerequisites: add source as the dependency

- `uv add --dev .`
- `uv build`
- `uv sync`

development:

- test: `mcp dev mcp/kb_exploer.py`
- install to claude: `mcp install mcp/kb_exploer.py --with-editable .`
