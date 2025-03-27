from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer
import psycopg2
import subprocess
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
            LIMIT 2;
        """, (embedding,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        return JSONResponse({"answer": f"[DB ERROR] {str(e)}"})

    if not rows:
        return JSONResponse({"answer": "No relevant data found."})

    # Step 3: Build the prompt for Mistral-Instruct format
    context = "\n\n".join([row[0] for row in rows])[:1000]  # keep it tight
    prompt = f"""<s>[INST] You are a helpful assistant specializing in sustainable building and Environmental Product Declarations (EPDs).
Please answer based only on the context. If the context does not contain enough information, say \"Not enough information.\"
Do not repeat the prompt. Please answer concisely.

Question: {question}

Context:
{context}
[/INST]"""

    print("[INFO] Prompt constructed.")
    print(prompt)

    # Step 4: Run llama.cpp
    try:
        result = subprocess.run(
            [
                "../llama.cpp/build/bin/llama-cli",
                "-m", "../llama.cpp/models/mistral-7b-instruct-v0.1.Q4_K_M.gguf",
                "--prompt", prompt,
                "-n", "256",
                "--temp", "0.7",
                "--top-p", "0.95",
                "--repeat_penalty", "1.2",
            ],
            text=True,
            capture_output=True
        )
        # print("[DEBUG] llama.cpp stdout:\n", result.stdout)
        # print("[DEBUG] llama.cpp stderr:\n", result.stderr)

        answer = result.stdout.strip()

        if "[end of text]" in answer:
            answer = answer.split("[end of text]")[0].strip()
        print("[INFO] Model output:", answer[:200], "..." if len(answer) > 200 else "")
        return JSONResponse({"answer": answer})
    except Exception as e:
        return JSONResponse({"answer": f"[LLM ERROR] {str(e)}"})
