import psycopg
import numpy as np
import pymupdf
from sentence_transformers import SentenceTransformer
from config import settings
from pathlib import Path
import base64
from io import BytesIO

# TODO: Logging module. Support RICH for clean console output, and JSON for production (easy to grep)

# Move this into running on cloud-storage in production.
# I'm thinking this makes sense as CRON/event-driven. Probably build a 'connector' approach 
# So we can easily add/remove sources. For simplicity, I would manage it via Terraform/DynamoDB.
DOCUMENTS_PATH = Path("pdfs/tudor/royal/")

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

def extract_images_from_page(doc, page_num):
    """Extract images from a PDF page"""
    page = doc[page_num]
    images = []
    
    image_list = page.get_images()
    
    for img_index, img in enumerate(image_list):
        xref = img[0]
        pix = pymupdf.Pixmap(doc, xref)

        # CMYK conversion to RGB
        if pix.n - pix.alpha > 3:  
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        
        img_data = pix.tobytes("png")
        images.append({
            'page': page_num,
            'index': img_index,
            'data': img_data
        })
        pix = None
    
    return images

def main():
    """Connects to the DB, processes documents (PDFs for now), creates embeddings, and stores them."""
    # TODO: I need to check if psycopg handles pooling. I probably should do dependencies/ and
    # create singleton instances that let me handle more intricate settings like Pools & Connection mgmt
    # Does @lru_cache make sense here.
    # It also let's us handle some exception handling more easily, maybe?
    conn = psycopg.connect(settings.postgres_dsn)
    cur = conn.cursor()
        
    # Do I want to look at having executable SQL scripts in a dir for version control?
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()
    
    cur.execute("DROP TABLE IF EXISTS documents CASCADE;")
    cur.execute("DROP TABLE IF EXISTS document_images CASCADE;")
    
    # TODO: Migrate IDs to UUIDs. I can do things like prefix by source/type, etc later.
    # TODO: Adjust embedding dimension based on model. What's the safe way to add parameter to the SQL again?
    cur.execute("""
    CREATE TABLE documents (
        id SERIAL PRIMARY KEY,
        content TEXT,
        embedding VECTOR(384),
        source_file TEXT,
        page_num INTEGER,
        metadata JSONB
    );
    """
    )
    
    # For future image handling
    cur.execute("""
    CREATE TABLE document_images (
        id SERIAL PRIMARY KEY,
        document_id INTEGER REFERENCES documents(id),
        image_data BYTEA,
        page_num INTEGER,
        image_index INTEGER,
        caption TEXT,
        embedding VECTOR(512)  -- For future CLIP embeddings
    );
    """)
    
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
        
        doc = pymupdf.open(filepath)
        
        full_text = ""
        page_texts = []
        
        for page_num, page in enumerate(doc):
            # Get text with layout preservation
            # or "blocks" for structured extraction
            text = page.get_text("text")  
            
            if text.strip():
                page_texts.append((page_num, text))
                full_text += text + "\n"
            
            # TODO: image extraction
            # images = extract_images_from_page(doc, page_num)
            # for img in images:
            #     # Store images for future processing (OCR, CLIP embeddings, etc.)
            #     cur.execute(
            #         "INSERT INTO document_images (page_num, image_index, image_data) VALUES (%s, %s, %s)",
            #         (page_num, img['index'], img['data'])
            #     )
        
        doc.close()
        
        if not full_text.strip():
            # TODO: change to warn once logging
            print(f"Warning: Could not extract text from {filepath.name}.")
            continue
            
        chunks = split_text(full_text)
        print(f"Embedding {len(chunks)} chunks...")
        embeddings = model.encode(chunks)

        for content, embedding in zip(chunks, embeddings):
            cur.execute(
                "INSERT INTO documents (content, embedding, source_file) VALUES (%s, %s, %s)",
                (content, embedding.tolist(), filepath.name)
            )
        conn.commit()

    print("Creating IVFFlat index...")
    cur.execute(
        "CREATE INDEX ON documents USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);"
    )
    conn.commit()
    cur.close()
    conn.close()
    print("\nIngestion complete.")

if __name__ == "__main__":
    main()