import json

from agno.embedder.google import GeminiEmbedder
from agno.knowledge.pdf import PDFKnowledgeBase, PDFReader
from agno.vectordb.pgvector import PgVector
from pydantic import BaseModel, Field

from lib.utils import filename


class Config(BaseModel):
    # example: "postgresql://user:password@127.0.0.1:5432/db"
    pg_url: str = Field(description="KB database URL")


def generate_kb_entry(resourceUrl: str, config: Config, upsert=False):
    c = _load_config(config)
    kb = PDFKnowledgeBase(
        path=resourceUrl,
        vector_db=PgVector(
            table_name="pdf_documents",
            db_url=c.pg_url,
            embedder=GeminiEmbedder(),
        ),
        reader=PDFReader(chunk=True),
    )
    kb.load(
        recreate=False,
        upsert=upsert,
    )


def _load_config(config):
    with open(config, "r") as file:
        json_data = json.load(file)
    c = Config.model_validate(json_data)
    return c


def remove_kb_entry(
    resourceUrl: str,
    config: Config,
):
    c = _load_config(config)
    kb = PDFKnowledgeBase(
        path=resourceUrl,
        vector_db=PgVector(
            table_name="pdf_documents",
            db_url=c.pg_url,
            embedder=GeminiEmbedder(),
        ),
        reader=PDFReader(chunk=True),
    )
    name = filename(resourceUrl)
    if not kb.vector_db.name_exists(name):
        print(f"No such entry: {name}")
        return

    # TODO: Remove the entry in the database
