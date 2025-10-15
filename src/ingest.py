import psycopg
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from config import settings
from pathlib import Path

# TODO: Logging module. Support RICH for clean console output, and JSON for production (easy to grep)

# Move this into running on cloud-storage in production.
# I'm thinking this makes sense as CRON/event-driven. Probably build a 'connector' approach 
# So we can easily add/remove sources. For simplicity, I would manage it via Terraform/DynamoDB.
DOCUMENTS_PATH = Path("documents/")

def split_text(text, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """
    Splits text into overlapping chunks
    There's a variety of ways to handle semantic splitting.
    But starting simple makes sense.
    """
    # better for memory to use a generator here later.
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
    return chunks

def main():
    """Connects to the DB, processes documents (PDFs for now), creates embeddings, and stores them."""
    # TODO: I need to check if psycopg handles pooling. I probably should do dependencies/ and
    # create singleton instances that let me handle more intricate settings like Pools & Connection mgmt
    # Does @lru_cache make sense here.
    # It also let's us handle some exception handling more easily, maybe?
    conn = psycopg.connect(dsn=settings.postgres_dsn) 
    cur = conn.cursor()
        
    # Do I want to look at having executable SQL scripts in a dir for version control?
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()
    cur.execute("DROP TABLE IF EXISTS documents;")
    # TODO: Migrate IDs to UUIDs. I can do things like prefix by source/type, etc later.
    # TODO: Adjust embedding dimension based on model. What's the safe way to add parameter to the SQL again?
    cur.execute("""
    CREATE TABLE documents (
        id SERIAL PRIMARY KEY,
        content TEXT,
        embedding VECTOR(384)
    """
    )
    conn.commit()
    # TODO: add detect device logic
    # TODO: move model into dependencies for singleton handling
    model = SentenceTransformer(settings.embedding_model_name, device='cpu')

    # Starting with a naive approach.
    # This would turn into an approach by type and potentially source that has distinct
    # downstream processing that handles it more cleanly.
    # e.g. PowerPoints -> transcribe -> by slide -> chunk -> embed
    # e.g. Word docs -> extract text -> chunk -> embed
    # e.g. CSVs -> parse -> chunk -> embed
    # e.g. Webpages -> scrape -> chunk -> embed
    pdf_files = list(DOCUMENTS_PATH.glob("*.pdf"))
    
    for filepath in pdf_files:
        print(f"Processing {filepath.name} ...")
        reader = PdfReader(filepath)
        # TODO: less memory intensive. Really bad on massive PDFs.
        # How do we want to handle tables etc
        full_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        chunks = split_text(full_text)

        if not chunks:
            # TODO: change to warn once logging
            print(f"Warning: Could not extract text from {filepath.name}.")
            continue
        print(f"Embedding {len(chunks)} chunks...")
        embeddings = model.encode(chunks)

        for content, embedding in zip(chunks, embeddings):
            cur.execute(
                "INSERT INTO documents (content, embedding) VALUES (%s, %s)",
                (content, np.array(embedding))
            )

        print("Creating IVFFlat index...")
        cur.execute(
            "CREATE INDEX ON documents USING ivfflat (embedding vector_12_ops) WITH (lists = 100);"
        )
        conn.commit()
        cur.close()
        conn.close()
        print("\nIngestion complete.")

if __name__ == "__main__":
    main()