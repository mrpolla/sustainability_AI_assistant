import os
import json
import psycopg2
import psycopg2.extras
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# === CONFIG ======================
load_dotenv()
#embedding_transformer = "BAAI/bge-large-en-v1.5"
table = "embeddings_large"
embedding_transformer = "BAAI/bge-large-en-v1.5"
input_file = "data/chunks/theory_chunks_tagged.json"
embedding_database = "pgvector"
recreate_table = False

DB_PARAMS = {
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PASSWORD"),
    "host": os.getenv("PG_HOST"),
    "port": os.getenv("PG_PORT")
}
db_name = os.getenv("PG_NAME", "epd_vectors")

BATCH_SIZE = 4  # small batch size to avoid memory issues
# ================================

def load_chunks(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def connect_pg():
    return psycopg2.connect(dbname=db_name, **DB_PARAMS)

def create_table(conn, dim):
    with conn.cursor() as cur:
        if recreate_table:
            cur.execute(f"DROP TABLE IF EXISTS {table}")
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                chunk_id TEXT PRIMARY KEY,
                process_id TEXT,
                embedding VECTOR({dim}),
                chunk TEXT,
                metadata JSONB
            )
        """)
        conn.commit()

def insert_embedding(conn, chunk_id, process_id, embedding, chunk_text, metadata):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO embeddings_small (chunk_id, process_id, embedding, chunk, metadata)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO NOTHING
            """,
            (chunk_id, process_id, embedding, chunk_text, json.dumps(metadata))
        )

def embed_chunks():
    print(f"📦 Loading model: {embedding_transformer}...")
    model = SentenceTransformer(embedding_transformer, device="cpu")  # safer on CPU
    dim = len(model.encode("test"))
    print(f"✅ Model loaded (dim={dim})")

    print(f"📄 Loading chunks from {input_file}...")
    chunks = load_chunks(input_file)
    print(f"🔢 {len(chunks)} chunks loaded")

    print("🛢️ Connecting to PostgreSQL...")
    conn = connect_pg()
    create_table(conn, dim)

    print("✨ Embedding and inserting in batches...")
    for i in tqdm(range(0, len(chunks), BATCH_SIZE)):
        batch = chunks[i:i + BATCH_SIZE]
        texts = [c["chunk"].strip() for c in batch]
        embeddings = model.encode(texts, show_progress_bar=False)

        for chunk, embedding in zip(batch, embeddings):
            chunk_id = chunk["chunk_id"]
            metadata = chunk["metadata"]
            process_id = metadata.get("product_id") or metadata.get("process_id") or None
            insert_embedding(conn, chunk_id, process_id, embedding.tolist(), chunk["chunk"], metadata)

        conn.commit()

    conn.close()
    print("✅ All chunks embedded and stored.")

if __name__ == "__main__":
    embed_chunks()
