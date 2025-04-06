from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer
import psycopg2
import os
import logging
import traceback
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
try:
    embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    logger.info("Embedding model loaded successfully")
except Exception as e:
    logger.exception("Failed to load embedding model")
    embedding_model = None  # Will handle this case in the endpoints

# DB connection settings
DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

def get_db_connection():
    """
    Create a database connection with proper error handling
    """
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except Exception as e:
        logger.exception("Failed to connect to database")
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )

@app.post("/ask")
async def ask_question(data: QuestionRequest):
    question = data.question.strip()
    document_ids = data.documentIds or []
    
    # Input validation
    if not question:
        return JSONResponse(
            status_code=400,
            content={"answer": "Question cannot be empty."}
        )
    
    logger.info(f"[INFO] Question received: {question}")
    if document_ids:
        logger.info(f"[INFO] Selected documents: {document_ids}")

    # Check if embedding model is available
    if embedding_model is None:
        return JSONResponse(
            status_code=503,
            content={"answer": "Embedding model is not available. Please try again later."}
        )

    # Step 1: Create embedding
    try:
        embedding = embedding_model.encode(question).tolist()
    except Exception as e:
        logger.exception("Error during embedding")
        return JSONResponse(
            status_code=500,
            content={"answer": f"Failed to process your question: {str(e)}"}
        )

    # Step 2: Retrieve relevant context from DB
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
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
        except Exception as db_error:
            logger.exception("Database query error")
            raise HTTPException(
                status_code=500,
                detail=f"Database query error: {str(db_error)}"
            )
        finally:
            cur.close()
            conn.close()

        if not rows:
            logger.warning("No relevant chunks found.")
            return JSONResponse(
                content={"answer": "I couldn't find relevant information to answer your question. Try a different question or select different products."}
            )

        logger.info(f"Retrieved {len(rows)} chunks")

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception("Unexpected database error")
        return JSONResponse(
            status_code=500,
            content={"answer": f"An unexpected error occurred while retrieving data: {str(e)}"}
        )

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
        if not answer or not isinstance(answer, str):
            logger.warning(f"LLM returned invalid answer: {answer}")
            return JSONResponse(
                content={"answer": "I'm sorry, I couldn't generate a proper response. Please try again."}
            )
            
        logger.info("LLM returned result.")
        return JSONResponse(content={"answer": answer})
    except Exception as e:
        logger.exception("Inference failed")
        return JSONResponse(
            status_code=503,
            content={"answer": f"I'm sorry, I'm having trouble generating a response right now. Please try again later. (Error: {str(e)})"}
        )

@app.post("/search")
async def search_products(data: SearchRequest):
    search_term = data.searchTerm.strip() if data.searchTerm else ""
    logger.info(f"[INFO] Search term received: {search_term}")

    if not search_term:
        return JSONResponse(content={"items": []})

    # Search for products in the database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
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
        except Exception as query_error:
            logger.exception("Database query error during product search")
            raise HTTPException(
                status_code=500,
                detail=f"Database query error: {str(query_error)}"
            )
        finally:
            cur.close()
            conn.close()

        if not rows:
            logger.warning("No products found matching the search term.")
            return JSONResponse(content={"items": []})

        # Format results for the frontend
        items = [{"id": str(row[0]), "name": row[1], "description": row[2]} for row in rows]
        logger.info(f"Found {len(items)} products matching the search term.")
        
        return JSONResponse(content={"items": items})
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        error_msg = f"Unexpected error during product search: {str(e)}"
        logger.exception(error_msg)
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500, 
            content={"error": error_msg}
        )

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Simple health check endpoint to verify the API is running
    """
    try:
        # Check database connection
        conn = get_db_connection()
        conn.close()
        
        # Return status
        return JSONResponse(
            content={
                "status": "ok",
                "database": "connected",
                "embedding_model": "loaded" if embedding_model is not None else "not_loaded"
            }
        )
    except Exception as e:
        logger.exception("Health check failed")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": str(e),
                "embedding_model": "loaded" if embedding_model is not None else "not_loaded"
            }
        )

@app.post("/products")
async def get_all_products():
    """
    Get all product names for autocomplete functionality
    """
    logger.info("[INFO] Fetching all product names for autocomplete")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Get all product names and IDs
            cur.execute("""
                SELECT process_id, name_en 
                FROM products 
                ORDER BY name_en
            """)
            
            rows = cur.fetchall()
        except Exception as query_error:
            logger.exception("Database query error while fetching product names")
            raise HTTPException(
                status_code=500,
                detail=f"Database query error: {str(query_error)}"
            )
        finally:
            cur.close()
            conn.close()

        # Format products for the frontend
        products = [{"id": str(row[0]), "name": row[1]} for row in rows]
        logger.info(f"Fetched {len(products)} product names")
        
        return JSONResponse(content={"products": products})
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        error_msg = f"Unexpected error while fetching product names: {str(e)}"
        logger.exception(error_msg)
        return JSONResponse(
            status_code=500, 
            content={"error": error_msg}
        )