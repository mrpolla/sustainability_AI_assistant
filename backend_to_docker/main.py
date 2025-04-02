from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer
import psycopg2
import os
from dotenv import load_dotenv
from llm_utils import query_llm

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

# Request schema
class QuestionRequest(BaseModel):
    question: str

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
    print(f"[INFO] Question received: {question}")

    # Step 1: Create embedding
    try:
        embedding = embedding_model.encode(question).tolist()
    except Exception as e:
        return JSONResponse({"answer": f"[EMBEDDING ERROR] {str(e)}"})

    # Step 2: Retrieve relevant context from DB
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        cur.execute("""
            SELECT chunk
            FROM epd_embeddings
            ORDER BY embedding <-> %s::vector
            LIMIT 5;
        """, (embedding,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Log the retrieved chunks
        print("[INFO] Retrieved chunks:")
        for i, row in enumerate(rows, start=1):
            print(f"Chunk {i}: {row[0]}")  # Print first 200 characters of each chunk
    except Exception as e:
        return JSONResponse({"answer": f"[DB ERROR] {str(e)}"})

    if not rows:
        return JSONResponse({"answer": "No relevant data found."})

    # Step 3: Construct prompt
    context = "\n\n".join([row[0] for row in rows])
    prompt = f"""You are a helpful assistant that only uses the provided context to answer questions.

Question: {question}

Context:
{context}

Answer:"""

    print("[INFO] Prompt ready, sending to inference API")
    print(prompt)


    # Step 4: Send prompt to inference service (Kaggle/Colab/HF)
    try:
        answer = query_llm(prompt)
        print("[INFO] Inference result:", answer[:200], "..." if len(answer) > 200 else "")
        return JSONResponse({"answer": answer})
    except Exception as e:
        return JSONResponse({"answer": f"[INFERENCE ERROR] {str(e)}"})
