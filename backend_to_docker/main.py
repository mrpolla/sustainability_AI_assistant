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
import math

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
    indicatorIds: list[str] = []
    llmModel: str = "Llama-3.2-1B-Instruct"

class SearchRequest(BaseModel):
    searchTerm: str

# Load embedding model
try:
    embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    logger.info("Embedding model loaded successfully")
except Exception as e:
    logger.exception("Failed to load embedding model")
    embedding_model = None  # Will handle this case in the endpoints

# DB data connection settings
DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}
# PG Vector database connection settings
PG_PARAMS = {
    "host": os.getenv("PG_HOST"),
    "dbname": os.getenv("PG_NAME"),
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PASSWORD"),
    "port": os.getenv("PG_PORT")
}

def get_db_connection():
    """
    Create a database connection to EPD_data with proper error handling
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
def get_pg_connection():
    """
    Create a database connection to EPD_vectors with proper error handling
    """
    try:
        conn = psycopg2.connect(**PG_PARAMS)
        return conn
    except Exception as e:
        logger.exception("Failed to connect to database")
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )

def sanitize_for_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj

@app.post("/ask")  # Simple ask endpoint
async def ask_simple(data: QuestionRequest):
    question = data.question.strip()
    llm_model = data.llmModel
    
    if not question:
        return JSONResponse(
            status_code=400,
            content={"answer": "Question cannot be empty."}
        )

    logger.info(f"[INFO] Simple ask received: {question}")
    logger.info(f"[INFO] Selected LLM: {llm_model}")

    try:
        answer = query_llm(question, model_name=llm_model)
        return JSONResponse(content={"answer": answer})
    except Exception as e:
        logger.exception("Simple inference failed")
        return JSONResponse(
            status_code=503,
            content={"answer": f"LLM error: {str(e)}"}
        )


@app.post("/askrag")
async def ask_question(data: QuestionRequest):
    question = data.question.strip()
    document_ids = data.documentIds or []
    indicator_ids = []  # Initialize this since it's not in the model yet
    if hasattr(data, 'indicatorIds'):  # Check if indicatorIds exists in the request
        indicator_ids = data.indicatorIds or []
    llm_model = data.llmModel
    
    logger.info(f"[DEBUG] Received request data: {data}")
    
    # Input validation
    if not question:
        return JSONResponse(
            status_code=400,
            content={"answer": "Question cannot be empty."}
        )
    
    logger.info(f"[INFO] Question received: {question}")
    logger.info(f"[INFO] Selected LLM: {llm_model}")
    if document_ids:
        logger.info(f"[INFO] Selected products: {document_ids}")
    if indicator_ids:
        logger.info(f"[INFO] Selected indicators: {indicator_ids}")

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
        conn = get_pg_connection()
        cur = conn.cursor()
        
        try:
            # Different query strategies based on what filters are provided
            if document_ids and indicator_ids:
                # Filter by both product IDs and indicator IDs
                # Since we don't have a direct way to filter by indicators in the current schema,
                # we'll use a simplified approach:
                # 1. Use product IDs to filter chunks
                # 2. Include indicator info in the prompt for the LLM
                product_placeholders = ', '.join(['%s'] * len(document_ids))
                cur.execute(f"""
                    SELECT chunk
                    FROM embeddings
                    WHERE process_id IN ({product_placeholders})
                    ORDER BY embedding <-> %s::vector
                    LIMIT 5;
                """, (*document_ids, embedding))
            
            elif document_ids:
                # If only product IDs are provided, filter by products only
                product_placeholders = ', '.join(['%s'] * len(document_ids))
                cur.execute(f"""
                    SELECT chunk
                    FROM embeddings
                    WHERE process_id IN ({product_placeholders})
                    ORDER BY embedding <-> %s::vector
                    LIMIT 5;
                """, (*document_ids, embedding))
            
            else:
                # If no product filters provided, return the most semantically relevant chunks
                cur.execute("""
                    SELECT chunk
                    FROM embeddings
                    ORDER BY embedding <-> %s::vector
                    LIMIT 5;
                """, (embedding,))
                
            rows = cur.fetchall()

            # Write chunks to a file one by one (for debugging)
            working_directory = os.getcwd()
            file_path = os.path.join(working_directory, "fetched_chunks.txt")

            with open(file_path, "w") as file:
                for row in rows:
                    file.write(f"{row[0]}\n\n")
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

    # Step 3: Construct prompt with product and indicator context
    chunks_context = "\n\n".join([row[0] for row in rows])
    
    # Add product and indicator context to the prompt
    product_context = ""
    if document_ids:
        product_context = f"The question relates to these product IDs: {', '.join(document_ids)}.\n"
    
    indicator_context = ""
    if indicator_ids:
        indicator_context = f"The question focuses on these environmental indicators: {', '.join(indicator_ids)}.\n"
    
    prompt = f"""You are a helpful assistant that only uses the provided context to answer questions.

Question: {question}

{product_context}{indicator_context}
Context:
{chunks_context}

Answer:"""

    logger.info("Prompt constructed. Sending to inference...")

    # Step 4: Send prompt to inference service
    try:
        logger.info(f"Calling LLM with model key: {llm_model}")
        logger.info(f"Sending prompt: {prompt}")
        answer = query_llm(prompt, model_name=llm_model)
        
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
async def search_products(data: dict):
    product_name = data.get("product_name", "").strip()
    logger.info(f"[INFO] Search filters received: {data}")

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        try:
            filters = []
            values = []

            if product_name:
                filters.append("""
                    (
                        name_en ILIKE %s OR
                        name_en_ai ILIKE %s
                    )
                """)
                values.extend([f"%{product_name}%"] * 2)

            if data.get("category_level_1"):
                filters.append("category_level_1 = %s")
                values.append(data["category_level_1"])

            if data.get("category_level_2"):
                filters.append("category_level_2 = %s")
                values.append(data["category_level_2"])

            if data.get("category_level_3"):
                filters.append("category_level_3 = %s")
                values.append(data["category_level_3"])

            if data.get("use_case"):
                filters.append("""
                    EXISTS (
                        SELECT 1 FROM uses u
                        WHERE u.process_id = products.process_id
                        AND u.use_case = %s
                    )
                """)
                values.append(data["use_case"])

            if data.get("material"):
                filters.append("""
                    EXISTS (
                        SELECT 1 FROM materials m
                        WHERE m.process_id = products.process_id
                        AND m.material = %s
                    )
                """)
                values.append(data["material"])

            where_clause = "WHERE " + " AND ".join(filters) if filters else ""

            logger.info(f"[DEBUG] WHERE clause: {where_clause}")
            logger.info(f"[DEBUG] Query values: {values}")
            cur.execute(f"""
                SELECT 
                    process_id, 
                    name_en,
                    name_en_ai,
                    description_en,
                    description_en_ai,
                    short_desc_en_ai,
                    tech_descr_en, 
                    tech_descr_en_ai,
                    category_level_1,
                    category_level_2,
                    category_level_3
                FROM products
                {where_clause}
                LIMIT 20;
            """, tuple(values))

            rows = cur.fetchall()
            if not rows:
                logger.info("No products matched the filters/search.")
                return JSONResponse(content={"items": []})

            items = []
            for row in rows:
                process_id, name_en, name_en_ai, description_en, description_en_ai, short_desc_en_ai, tech_en, tech_en_ai, cat1, cat2, cat3 = row
                items.append({
                    "process_id": str(process_id),
                    "name_en": name_en,
                    "name_en_ai": name_en_ai,
                    "description_en": description_en,
                    "description_en_ai": description_en_ai,
                    "short_description_ai": short_desc_en_ai,
                    "tech_description_en": tech_en,
                    "tech_description_en_ai": tech_en_ai,
                    "category_level_1": cat1,
                    "category_level_2": cat2,
                    "category_level_3": cat3
                })

            logger.info(f"Found {len(items)} products matching filters.")
            return JSONResponse(content={"items": items})

        except Exception as query_error:
            logger.exception("Database query error during product search")
            raise HTTPException(status_code=500, detail=str(query_error))

        finally:
            cur.close()
            conn.close()

    except Exception as e:
        logger.exception("Search endpoint failure")
        return JSONResponse(
            status_code=500,
            content={"error": f"Unexpected error during search: {str(e)}"}
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

@app.get("/filters")
async def get_filter_options():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT DISTINCT category_level_1 FROM products WHERE category_level_1 IS NOT NULL;")
            level1 = [row[0] for row in cur.fetchall()]

            cur.execute("SELECT DISTINCT category_level_2 FROM products WHERE category_level_2 IS NOT NULL;")
            level2 = [row[0] for row in cur.fetchall()]

            cur.execute("SELECT DISTINCT category_level_3 FROM products WHERE category_level_3 IS NOT NULL;")
            level3 = [row[0] for row in cur.fetchall()]

            cur.execute("SELECT DISTINCT use_case FROM uses WHERE use_case IS NOT NULL;")
            use_cases = [row[0] for row in cur.fetchall()]

            cur.execute("SELECT DISTINCT material FROM materials WHERE material IS NOT NULL;")
            materials = [row[0] for row in cur.fetchall()]
        finally:
            cur.close()
            conn.close()

        return JSONResponse(content={
            "category_level_1": level1,
            "category_level_2": level2,
            "category_level_3": level3,
            "use_cases": use_cases,
            "materials": materials
        })
    except Exception as e:
        logger.exception("Error fetching filter data")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to fetch filters: {str(e)}"}
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
    Get all indicators with metadata from the indicators table
    """
    logger.info("[INFO] Fetching indicators with descriptions from database")

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT 
                    indicator_key, 
                    name, 
                    short_description, 
                    long_description
                FROM indicators
                WHERE indicator_key IS NOT NULL AND name IS NOT NULL
                ORDER BY indicator_key;
            """)
            rows = cur.fetchall()

        except Exception as query_error:
            logger.exception("Database query error while fetching indicators")
            raise HTTPException(status_code=500, detail=str(query_error))

        finally:
            cur.close()
            conn.close()

        indicators = [
            {
                "key": indicator_key,
                "name": name,
                "short_description": short_desc,
                "long_description": long_desc
            }
            for indicator_key, name, short_desc, long_desc in rows
        ]

        logger.info(f"Fetched {len(indicators)} indicators")
        return JSONResponse(content={"indicators": indicators})

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error fetching indicators")
        return JSONResponse(
            status_code=500,
            content={"error": f"Unexpected error: {str(e)}"}
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
            
            # Get the category of the first product for now
            cur.execute("""
                SELECT category_level_1, category_level_2, category_level_3
                FROM products
                WHERE process_id = %s
            """, (product_ids[0],))
            category_row = cur.fetchone()
            category_level_1, category_level_2, category_level_3 = category_row


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
            
            # Get relevant statistics for the indicators and modules
            module_names = list(set(row[3] for row in lcia_rows + exchange_rows if row[3]))

            if module_names:
                stats_indicator_placeholders = ', '.join(['%s'] * len(indicator_keys))
                stats_module_placeholders = ', '.join(['%s'] * len(module_names))

                cur.execute(f"""
                    SELECT indicator_key, module, mean, min, max, unit
                    FROM indicator_statistics
                    WHERE indicator_key IN ({stats_indicator_placeholders})
                    AND module IN ({stats_module_placeholders})
                    AND category_level_1 = %s
                    AND category_level_2 = %s
                    AND category_level_3 = %s
                """, tuple(indicator_keys) + tuple(module_names) + (category_level_1, category_level_2, category_level_3))

                stats_rows = cur.fetchall()
            else:
                stats_rows = []

            logger.info(f"Fetched {len(stats_rows)} statistics rows")
            for row in stats_rows:
                logger.info(f"Stat row: indicator={row[0]}, module={row[1]}, mean={row[2]}, min={row[3]}, max={row[4]}, unit={row[5]}")

            # Group stats by indicator_key and module
            indicator_stats = {}
            for indicator_key, module, mean, min_val, max_val, unit in stats_rows:
                if indicator_key not in indicator_stats:
                    indicator_stats[indicator_key] = {}
                indicator_stats[indicator_key][module] = {
                    "mean": float(mean) if mean is not None else None,
                    "min": float(min_val) if min_val is not None else None,
                    "max": float(max_val) if max_val is not None else None,
                    "unit": unit
                }
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
            # logger.info(f"[LCIA] {row}")
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
            # logger.info(f"[EXCHANGE] {row}")
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
                    "key": indicator_key,
                    "unit": data.get("unit", ""),
                    "category": f"{category_level_1} / {category_level_2} / {category_level_3}",
                    "stats": indicator_stats.get(indicator_key, {}),
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
        
        result = sanitize_for_json(result)
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