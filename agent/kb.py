import json

from agno.embedder.google import GeminiEmbedder
from agno.knowledge.pdf import PDFKnowledgeBase, PDFReader
from agno.vectordb.pgvector import PgVector
from pydantic import BaseModel, Field
from sqlalchemy.sql.expression import delete, select


class Config(BaseModel):
    # example: "postgresql+psycopg://user:password@127.0.0.1:5432/db"
    pg_url: str = Field(description="KB database URL")


def list_kb_entries(config: str):
    c = _load_config(config)
    db: PgVector = PgVector(
        table_name="pdf_documents",
        db_url=c.pg_url,
        embedder=GeminiEmbedder(),
    )

    try:
        with db.Session() as sess, sess.begin():
            stmt = select(db.table.c.name).distinct()
            result = sess.execute(stmt)
            entries = "\n".join([row[0] for row in result])
            print(entries)
            return entries
    except Exception as e:
        print(f"Error getting document names from table '{db.table.fullname}': {e}")


def generate_kb_entry(resourceUrl: str, config: str, upsert=False):
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


def _load_config(config: str):
    with open(config, "r") as file:
        json_data = json.load(file)
    c = Config.model_validate(json_data)
    return c


def remove_kb_entry(
    name: str,
    config: str,
):
    c = _load_config(config)
    db: PgVector = PgVector(
        table_name="pdf_documents",
        db_url=c.pg_url,
        embedder=GeminiEmbedder(),
    )
    if not db.name_exists(name):
        print(f"No such entry: {name}")
        return

    try:
        with db.Session() as sess, sess.begin():
            stmt = delete(db.table).where(db.table.c.name == name)
            sess.execute(stmt)
            sess.commit()
    except Exception as e:
        print(f"Error getting count from table '{db.table.fullname}': {e}")
        sess.rollback()
