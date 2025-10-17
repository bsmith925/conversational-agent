import asyncio
import psycopg
from psycopg_pool import AsyncConnectionPool
import pymupdf
from sentence_transformers import SentenceTransformer
from config import settings
from pathlib import Path
import re
import hashlib
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from tqdm.asyncio import tqdm
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# How to annotate everything like PPT for sales etc
# VLM on bar graph for sales. Before or on-the-fly, catching strays etc. Lots of up-front work/guardrails
# e.g. 1MM powerpoints, lots of wasted compute up-front if 1% or less is queried
# at run-time, annotate on-the-fly and save it. Does annotation get used in retrieval?
# eventually link documents
# then you get into the realm of scoped-permissions of who can access what
# SSO has 'scopes' attached to the identity, can pass those through. Mirror folder permissions to db
# but that's a good bit of 'maintenance' on the db..but necessary I think

DOCUMENTS_PATH = Path("pdfs/adhd_meds/")

# Thread pool for CPU-bound operations (PDF processing, embeddings)
# Adjust based on CPU cores
CPU_EXECUTOR = ThreadPoolExecutor(max_workers=4)
# Process pool for parallel PDF extraction
PROCESS_EXECUTOR = ProcessPoolExecutor(max_workers=2)


def smart_split_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    respect_sentences: bool = True,
) -> List[Dict[str, Any]]:
    """
    Splits text into overlapping chunks with better semantic boundaries.
    Returns chunks with metadata about their content.
    """
    chunks = []

    if respect_sentences:
        # Split by sentences first
        sentences = re.split(r"(?<=[.!?])\s+", text)
        current_chunk = ""
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # If adding this sentence exceeds chunk_size, save current chunk
            if current_length + sentence_length > chunk_size and current_chunk:
                chunks.append({"text": current_chunk.strip(), "length": current_length})

                # Start new chunk with character-based overlap to avoid issues with abbreviations
                if len(current_chunk) > chunk_overlap:
                    overlap_text = current_chunk[-chunk_overlap:]
                else:
                    overlap_text = current_chunk
                current_chunk = overlap_text + " " + sentence
                current_length = len(current_chunk)
            else:
                current_chunk += " " + sentence
                current_length += sentence_length

        # the last chunk
        if current_chunk.strip():
            chunks.append({"text": current_chunk.strip(), "length": current_length})
    else:
        # Fallback to character-based splitting
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]

            # Try to break at a sentence boundary
            if end < len(text):
                last_period = chunk_text.rfind(".")
                if last_period > chunk_size * 0.5:
                    chunk_text = text[start : start + last_period + 1]
                    end = start + last_period + 1

            chunks.append({"text": chunk_text.strip(), "length": len(chunk_text)})
            start = end - chunk_overlap

    return chunks


def extract_document_metadata(text: str, page_num: int) -> Dict[str, Any]:
    """
    Extract basic metadata from document text.

    TODO: Make this configurable via dataset config file for domain-specific patterns.
    For now, keeping it minimal and domain-agnostic.
    """
    metadata = {"page": page_num, "chunk_length": len(text)}

    # Future: Load patterns from config for domain-specific entity extraction
    # e.g., people_pattern, date_pattern, place_pattern from YAML config
    # maybe deeper calls to handle figured, tables, etc go inside here

    return metadata


def process_pdf_file(filepath: Path) -> List[Dict[str, Any]]:
    """
    Process a single PDF file and return chunks with metadata.
    This runs in a thread/process pool.
    """
    doc = pymupdf.open(filepath)
    all_chunks = []

    for page_num, page in enumerate(doc):
        text = page.get_text("text")

        if not text.strip():
            continue

        page_metadata = extract_document_metadata(text, page_num)

        page_chunks = smart_split_text(
            text, chunk_size=800, chunk_overlap=100, respect_sentences=True
        )

        # Add metadata to each chunk
        for chunk_index, chunk_data in enumerate(page_chunks):
            chunk_with_meta = {
                "text": chunk_data["text"],
                "page": page_num,
                "chunk_index": chunk_index,
                "metadata": {
                    **page_metadata,
                    "chunk_length": chunk_data["length"],
                    "source": filepath.name,
                },
                "source_file": filepath.name,
            }
            all_chunks.append(chunk_with_meta)

    doc.close()
    return all_chunks


def create_embeddings_batch(
    texts: List[str], model: SentenceTransformer
) -> List[List[float]]:
    """
    Create embeddings for a batch of texts.
    This runs in a thread pool for CPU-bound operations.
    """
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
    return [embedding.tolist() for embedding in embeddings]


async def process_pdf_async(
    filepath: Path, loop: asyncio.AbstractEventLoop
) -> List[Dict[str, Any]]:
    """
    Async wrapper for PDF processing using thread/process pool.
    """
    return await loop.run_in_executor(CPU_EXECUTOR, process_pdf_file, filepath)


async def create_embeddings_async(
    texts: List[str], model: SentenceTransformer, loop: asyncio.AbstractEventLoop
) -> List[List[float]]:
    """
    Async wrapper for embedding creation.
    """
    return await loop.run_in_executor(
        CPU_EXECUTOR, create_embeddings_batch, texts, model
    )


async def setup_database(pool: AsyncConnectionPool):
    """
    Setup database tables and extensions using psycopg3.
    """
    async with pool.connection() as aconn:
        async with aconn.cursor() as acur:
            # Create vector extension. Current image comes with it for prototyping
            await acur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            # Drop existing tables (only if allowed), just for prototyping. I can avoid re-creating volumes for now
            if settings.allow_db_recreation:
                logger.warning("Dropping existing tables (allow_db_recreation=True)")
                await acur.execute("DROP TABLE IF EXISTS documents CASCADE;")
                await acur.execute("DROP TABLE IF EXISTS document_images CASCADE;")
            else:
                logger.info("Skipping table drop (allow_db_recreation=False)")

            # Create documents table with unique constraint on content_hash
            # TODO: migrate id to uuid
            await acur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    content TEXT,
                    embedding VECTOR(384),
                    source_file TEXT,
                    page_num INTEGER,
                    chunk_index INTEGER,
                    metadata JSONB,
                    content_hash TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await acur.execute("""
                CREATE TABLE IF NOT EXISTS document_images (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id),
                    image_data BYTEA,
                    page_num INTEGER,
                    image_index INTEGER,
                    caption TEXT,
                    embedding VECTOR(512)
                );
            """)

            await aconn.commit()
            logger.info("Database tables created successfully")


async def create_indexes(pool: AsyncConnectionPool):
    """
    Create database indexes for optimized queries using psycopg3.
    """
    async with pool.connection() as aconn:
        async with aconn.cursor() as acur:
            logger.info("Creating indexes...")

            # Vector index for similarity search (using cosine distance to match query operator)
            await acur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_embedding 
                ON documents USING ivfflat (embedding vector_cosine_ops) 
                WITH (lists = 100);
            """)

            # Index on metadata for filtered searches
            await acur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_metadata 
                ON documents USING GIN (metadata);
            """)

            # Index on source and page for document navigation
            await acur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_source 
                ON documents (source_file, page_num);
            """)

            # Index on content hash for deduplication
            # TODO: evaluate if I'm getting dupes...write a test case
            await acur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_hash 
                ON documents (content_hash);
            """)

            # Analyze table to help query planner use indexes efficiently
            await acur.execute("ANALYZE documents;")

            await aconn.commit()
            logger.info("Indexes created successfully")


async def insert_chunks_executemany(
    pool: AsyncConnectionPool,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
) -> int:
    """
    Alternative insert method using executemany for better compatibility.
    """
    inserted = 0

    async with pool.connection() as aconn:
        async with aconn.cursor() as acur:
            batch_data = []
            for chunk, embedding in zip(chunks, embeddings):
                content_hash = hashlib.md5(chunk["text"].encode()).hexdigest()
                # Keep as string but will cast in SQL for robustness
                embedding_str = f"[{','.join(map(str, embedding))}]"
                batch_data.append(
                    (
                        chunk["text"],
                        embedding_str,
                        chunk["source_file"],
                        chunk["page"],
                        chunk["chunk_index"],
                        psycopg.types.json.Json(chunk["metadata"]),
                        content_hash,
                    )
                )

            # Batch with executemany, explicit vector cast
            query = """
                INSERT INTO documents 
                (content, embedding, source_file, page_num, chunk_index, metadata, content_hash) 
                VALUES (%s, %s::vector, %s, %s, %s, %s, %s)
                ON CONFLICT (content_hash) DO NOTHING
            """

            # Execute all inserts
            for data in batch_data:
                await acur.execute(query, data)
                if acur.rowcount > 0:
                    inserted += 1

            await aconn.commit()

    return inserted


async def process_pdfs_concurrently(
    pdf_files: List[Path],
    pool: AsyncConnectionPool,
    model: SentenceTransformer,
    batch_size: int = 100,
    max_concurrent_pdfs: int = 3,
):
    """
    Process multiple PDFs concurrently with batched database inserts.
    """
    loop = asyncio.get_event_loop()
    total_chunks_inserted = 0

    pbar = tqdm(total=len(pdf_files), desc="Processing PDFs")

    # Group
    for i in range(0, len(pdf_files), max_concurrent_pdfs):
        pdf_batch = pdf_files[i : i + max_concurrent_pdfs]
        pdf_tasks = [process_pdf_async(filepath, loop) for filepath in pdf_batch]

        logger.info(f"Processing PDFs: {[f.name for f in pdf_batch]}")
        pdf_results = await asyncio.gather(*pdf_tasks, return_exceptions=True)

        # Log any failures & continue
        for idx, result in enumerate(pdf_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process {pdf_batch[idx].name}: {result}")

        pbar.update(len(pdf_batch))

        # Flatten all chunks
        all_chunks = []
        for chunks in pdf_results:
            if not isinstance(chunks, Exception):
                all_chunks.extend(chunks)

        if not all_chunks:
            continue

        logger.info(f"Creating embeddings for {len(all_chunks)} chunks...")

        # Batch process embeddings & insert/
        # TODO: handle upsert
        # What's upsert implication on index again?
        for chunk_idx in range(0, len(all_chunks), batch_size):
            chunk_batch = all_chunks[chunk_idx : chunk_idx + batch_size]
            texts = [chunk["text"] for chunk in chunk_batch]

            embeddings = await create_embeddings_async(texts, model, loop)

            inserted = await insert_chunks_executemany(pool, chunk_batch, embeddings)
            total_chunks_inserted += inserted

            logger.info(f"Inserted {inserted} chunks (Total: {total_chunks_inserted})")

    pbar.close()
    return total_chunks_inserted


async def main():
    """
    Main async function to orchestrate concurrent document processing using psycopg3.
    """
    # Use async context manager for proper pool lifecycle management
    async with AsyncConnectionPool(
        conninfo=settings.postgres_dsn,
        min_size=5,
        max_size=20,
        timeout=60.0,
        max_waiting=100,
    ) as pool:
        try:
            await setup_database(pool)

            logger.info("Loading embedding model...")
            model = SentenceTransformer(settings.embedding_model_name, device="cpu")

            pdf_files = list(DOCUMENTS_PATH.glob("*.pdf"))
            logger.info(f"Found {len(pdf_files)} PDF files to process")

            if not pdf_files:
                logger.warning("No PDF files found in the specified directory")
                return

            total_inserted = await process_pdfs_concurrently(
                pdf_files,
                pool,
                model,
                batch_size=100,  # Adjust based on memory # TODO: dynamic this within memory constraint?
                max_concurrent_pdfs=3,  # Adjust based on system resources # TODO: dynamic here too
            )

            logger.info(f"Total chunks inserted: {total_inserted}")

            # Create indexes after all data is inserted
            await create_indexes(pool)

            logger.info("Ingestion complete!")

        except Exception as e:
            logger.error(f"Error during ingestion: {e}")
            raise
        finally:
            # Cleanup
            CPU_EXECUTOR.shutdown(wait=True)
            PROCESS_EXECUTOR.shutdown(wait=True)


if __name__ == "__main__":
    asyncio.run(main())
