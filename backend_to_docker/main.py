from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer
import psycopg2
import os
import logging
from dotenv import load_dotenv
from llm_utils import query_llm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()  # keep console output too
    ]
)
logger = logging.getLogger(__name__)

# Load env vars
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request schemas
class QuestionRequest(BaseModel):
    question: str
    documentIds: list[str] = []

class SearchRequest(BaseModel):
    searchTerm: str

# Load embedding model
embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# DB connection settings
DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

@app.post("/ask")
async def ask_question(data: QuestionRequest):
    question = data.question
    document_ids = data.documentIds
    logger.info(f"[INFO] Question received: {question}")
    
    if document_ids:
        logger.info(f"[INFO] Selected documents: {document_ids}")

    # Step 1: Create embedding
    try:
        embedding = embedding_model.encode(question).tolist()
    except Exception as e:
        logger.exception("Error during embedding")
        return JSONResponse({"answer": f"[EMBEDDING ERROR] {str(e)}"})

    # Step 2: Retrieve relevant context from DB
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # If document IDs are provided, only search within those documents
        if document_ids:
            placeholders = ', '.join(['%s'] * len(document_ids))
            cur.execute(f"""
                SELECT chunk
                FROM epd_embeddings
                WHERE product_id IN ({placeholders})
                ORDER BY embedding <-> %s::vector
                LIMIT 5;
            """, (*document_ids, embedding))
        else:
            cur.execute("""
                SELECT chunk
                FROM epd_embeddings
                ORDER BY embedding <-> %s::vector
                LIMIT 5;
            """, (embedding,))
            
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            logger.warning("No relevant chunks found.")
            return JSONResponse({"answer": "No relevant data found."})

        logger.info(f"Retrieved {len(rows)} chunks")
        for i, row in enumerate(rows, start=1):
            logger.info(f"Chunk {i}: {row[0]}")

    except Exception as e:
        logger.exception("Database error")
        return JSONResponse({"answer": f"[DB ERROR] {str(e)}"})

    # Step 3: Construct prompt
    context = "\n\n".join([row[0] for row in rows])
    prompt = f"""You are a helpful assistant that only uses the provided context to answer questions.

Question: {question}

Context:
{context}

Answer:"""

    logger.info("Prompt constructed. Sending to inference...")

    # Step 4: Send prompt to inference service
    try:
        answer = query_llm(prompt)
        logger.info("LLM returned result.")
        return JSONResponse({"answer": answer})
    except Exception as e:
        logger.exception("Inference failed")
        return JSONResponse({"answer": f"[INFERENCE ERROR] {str(e)}"})

@app.post("/search")
async def search_products(data: SearchRequest):
    search_term = data.searchTerm
    logger.info(f"[INFO] Search term received: {search_term}")

    if not search_term or len(search_term.strip()) == 0:
        return JSONResponse({"items": []})

    # Search for products in the database
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # Search in both name_en and description_en columns
        cur.execute("""
            SELECT process_id, name_en, description_en
            FROM products
            WHERE 
                name_en ILIKE %s OR
                description_en ILIKE %s
            LIMIT 20;
        """, (f"%{search_term}%", f"%{search_term}%"))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            logger.warning("No products found matching the search term.")
            return JSONResponse({"items": []})

        # Format results for the frontend
        items = [{"id": str(row[0]), "name": row[1]} for row in rows]
        logger.info(f"Found {len(items)} products matching the search term.")
        
        return JSONResponse({"items": items})
        
    except Exception as e:
        logger.exception("Database error during product search")
        return JSONResponse({"error": str(e)}, status_code=500)
