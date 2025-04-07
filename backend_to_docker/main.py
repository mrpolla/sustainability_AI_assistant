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
                    WHERE process_id IN ({placeholders})
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

            # Write chunks to a file one by one
            working_directory = os.getcwd()  # Get the current working directory
            file_path = os.path.join(working_directory, "fetched_chunks.txt")  # Construct the file path

            with open(file_path, "w") as file:
                for row in rows:
                    file.write(f"{row[0]}\n\n")  # Write each chunk followed by a newline
                    logger.info(f"Written chunk to file: {row[0]}")

            logger.info(f"Chunks saved to: {file_path}")

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
    
@app.post("/indicators")
async def get_all_indicators():
    """
    Get all unique indicator_key values from lcia_results and exchanges tables
    """
    logger.info("[INFO] Fetching all unique indicators for autocomplete")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Get unique indicator_key values from both tables
            cur.execute("""
                SELECT DISTINCT indicator_key FROM (
                    SELECT indicator_key FROM lcia_results
                    UNION
                    SELECT indicator_key FROM exchanges
                ) AS combined_indicators
                WHERE indicator_key IS NOT NULL AND indicator_key <> ''
                ORDER BY indicator_key
            """)
            
            rows = cur.fetchall()
        except Exception as query_error:
            logger.exception("Database query error while fetching indicators")
            raise HTTPException(
                status_code=500,
                detail=f"Database query error: {str(query_error)}"
            )
        finally:
            cur.close()
            conn.close()

        # Format indicators for the frontend
        indicators = [{"id": i, "name": row[0]} for i, row in enumerate(rows, start=1)]
        logger.info(f"Fetched {len(indicators)} unique indicators")
        
        return JSONResponse(content={"indicators": indicators})
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        error_msg = f"Unexpected error while fetching indicators: {str(e)}"
        logger.exception(error_msg)
        return JSONResponse(
            status_code=500, 
            content={"error": error_msg}
        )

@app.post("/compare")
async def compare_products(data: dict):
    """
    Fetches comparison data for selected products and indicators
    """
    product_ids = data.get("productIds", [])
    indicator_keys = data.get("indicatorKeys", [])
    
    logger.info(f"[INFO] Compare request received for {len(product_ids)} products and {len(indicator_keys)} indicators")
    
    if not product_ids:
        return JSONResponse(
            status_code=400,
            content={"error": "No products selected for comparison"}
        )
    
    if not indicator_keys:
        return JSONResponse(
            status_code=400,
            content={"error": "No indicators selected for comparison"}
        )
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Get product info first
            product_placeholders = ', '.join(['%s'] * len(product_ids))
            cur.execute(f"""
                SELECT process_id, name_en
                FROM products
                WHERE process_id IN ({product_placeholders})
            """, tuple(product_ids))
            
            product_rows = cur.fetchall()
            products = [
                {"id": str(row[0]), "name": row[1]} 
                for row in product_rows
            ]
            
            # Get LCIA results
            indicator_placeholders = ', '.join(['%s'] * len(indicator_keys))
            cur.execute(f"""
                SELECT l.process_id, l.indicator_key, l.unit, lm.module, lm.amount
                FROM lcia_results l
                JOIN lcia_moduleamounts lm ON l.lcia_id = lm.lcia_id
                WHERE l.process_id IN ({product_placeholders})
                AND l.indicator_key IN ({indicator_placeholders})
            """, tuple(product_ids) + tuple(indicator_keys))
            
            lcia_rows = cur.fetchall()
            
            # Get exchange results
            cur.execute(f"""
                SELECT e.process_id, e.indicator_key, e.unit, em.module, em.amount
                FROM exchanges e
                JOIN exchange_moduleamounts em ON e.exchange_id = em.exchange_id
                WHERE e.process_id IN ({product_placeholders})
                AND e.indicator_key IN ({indicator_placeholders})
            """, tuple(product_ids) + tuple(indicator_keys))
            
            exchange_rows = cur.fetchall()
            
        except Exception as query_error:
            logger.exception("Database query error during comparison")
            raise HTTPException(
                status_code=500,
                detail=f"Database query error: {str(query_error)}"
            )
        finally:
            cur.close()
            conn.close()
        
        # Process the data for the frontend
        comparison_data = {}
        
        # Process LCIA results
        for row in lcia_rows:
            logger.info(f"[LCIA] {row}")
            product_id, indicator_key, unit, module, amount = row
            
            if indicator_key not in comparison_data:
                comparison_data[indicator_key] = {
                    "name": indicator_key,
                    "unit": unit,
                    "products": {}
                }
            
            if str(product_id) not in comparison_data[indicator_key]["products"]:
                comparison_data[indicator_key]["products"][str(product_id)] = {
                    "modules": {}
                }
            
            if module:
                comparison_data[indicator_key]["products"][str(product_id)]["modules"][module] = amount
        
        # Process exchange results
        for row in exchange_rows:
            logger.info(f"[EXCHANGE] {row}")
            product_id, indicator_key, unit, module, amount = row
            
            if indicator_key not in comparison_data:
                comparison_data[indicator_key] = {
                    "name": indicator_key,
                    "unit": unit,
                    "products": {}
                }
            
            if str(product_id) not in comparison_data[indicator_key]["products"]:
                comparison_data[indicator_key]["products"][str(product_id)] = {
                    "modules": {}
                }
            
            if module:
                comparison_data[indicator_key]["products"][str(product_id)]["modules"][module] = amount
        
        # Format data for the frontend
        result = {
            "products": products,
            "indicators": [
                {
                    "name": indicator_key,
                    "unit": data.get("unit", ""),
                    "productData": [
                        {
                            "productId": product_id,
                            "modules": product_data.get("modules", {})
                        }
                        for product_id, product_data in data["products"].items()
                    ]
                }
                for indicator_key, data in comparison_data.items()
            ]
        }
        
        return JSONResponse(content=result)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        error_msg = f"Unexpected error during comparison: {str(e)}"
        logger.exception(error_msg)
        return JSONResponse(
            status_code=500, 
            content={"error": error_msg}
        )