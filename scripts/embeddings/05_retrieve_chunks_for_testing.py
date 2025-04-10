import os
import json
import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# === CONFIG ======================
load_dotenv()

embedding_transformer = "BAAI/bge-small-en-v1.5"
embedding_table = "embeddings_small"  # or embeddings_small
db_name = os.getenv("PG_NAME")

DB_PARAMS = {
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PASSWORD"),
    "host": os.getenv("PG_HOST"),
    "port": os.getenv("PG_PORT")
}

TOP_K = 5
SAVE_RESULTS = True
OUTPUT_PATH = "data/retrieval_log.json"
# ================================

def connect_pg():
    return psycopg2.connect(dbname=db_name, **DB_PARAMS)

def embed_query(query, model):
    return model.encode(query).tolist()

def search_similar_chunks(conn, query_embedding):
    with conn.cursor() as cur:
        base_query = f"""
            SELECT chunk_id, chunk, metadata, 1 - (embedding <#> %s::vector) AS score
            FROM {embedding_table}
            WHERE length(chunk) > 200
            ORDER BY embedding <#> %s::vector
            LIMIT %s;
        """
        cur.execute(base_query, (query_embedding, query_embedding, TOP_K))
        return cur.fetchall()

def save_chunks_to_file(query, results, output_path):
    output = {
        "query": query,
        "chunks": [
            {
                "chunk_id": r[0],
                "chunk": r[1],
                "metadata": r[2],
                "score": r[3]
            } for r in results
        ]
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"📁 Saved retrieval context to {output_path}")

def main():
    print(f"📦 Loading model: {embedding_transformer}...")
    model = SentenceTransformer(embedding_transformer, device="cpu")
    print(f"✅ Model loaded")

    query = input("🔍 Enter your query: ").strip()
    query_embedding = embed_query(query, model)

    print("🛢️ Connecting to DB and searching...")
    conn = connect_pg()
    results = search_similar_chunks(conn, query_embedding)
    conn.close()

    print(f"\n🔝 Top {TOP_K} results:")
    for i, (chunk_id, chunk, metadata, score) in enumerate(results):
        print(f"\n#{i+1} — Score: {score:.4f}")
        print(f"Chunk ID: {chunk_id}")
        print(f"Chunk: {chunk[:300]}{'...' if len(chunk) > 300 else ''}")
        print(f"Metadata: {json.dumps(metadata, indent=2)}")

    if SAVE_RESULTS:
        save_chunks_to_file(query, results, OUTPUT_PATH)

if __name__ == "__main__":
    main()
