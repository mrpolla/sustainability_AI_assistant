from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer
import psycopg2
import requests
import os
from dotenv import load_dotenv

# Load env
load_dotenv()

# Model for embeddings
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

class QuestionRequest(BaseModel):
    question: str

# DB params
DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

# App setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ask")
async def ask_question(data: QuestionRequest):
    question = data.question
    print(f"[INFO] Question received: {question}")

    # Step 1: Embed the question
    embedding = embedding_model.encode(question).tolist()

    # Step 2: Retrieve top 2 relevant chunks (smaller context)
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
    except Exception as e:
        return JSONResponse({"answer": f"[DB ERROR] {str(e)}"})

    if not rows:
        return JSONResponse({"answer": "No relevant data found."})

    # Step 3: Build prompt (simple instruction format for Ollama)
    context = "\n\n".join([row[0] for row in rows])
    print(context)
    # context = "\n\n".join([row[0] for row in rows])[:1500]
    prompt = f"""You are a helpful assistant that only uses the provided context to answer questions.

Question: {question}

Context:
{context}

Answer:"""

    print("[INFO] Prompt constructed.")
    print(prompt)

    # Save prompt to file for debugging
    with open("debug_prompt.txt", "w") as f:
        f.write(prompt)

    # Step 4: Use Ollama API with phi3 model
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "phi3",
                "prompt": prompt,
                "stream": False
            }
        )
        result = response.json()
        answer = result.get("response", "").strip()
        print("[INFO] Ollama output:", answer[:200], "..." if len(answer) > 200 else "")
        return JSONResponse({"answer": answer})
    except Exception as e:
        return JSONResponse({"answer": f"[OLLAMA ERROR] {str(e)}"})