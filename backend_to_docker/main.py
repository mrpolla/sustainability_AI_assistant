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
from query_logger import QueryLogger
from typing import List

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
query_logger = QueryLogger()

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
class CompareAnalysisRequest(BaseModel):
    productIds: List[str]
    indicatorIds: List[str]
    llmModel: str = "Llama-3.2-1B-Instruct"

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

def classify_question(question: str) -> str:
    """
    Classifies a user's sustainability question into a known category label.
    """
    classification_prompt = f"""
You are a classifier that analyzes sustainability-related questions about building products, circularity, and environmental indicators.

Classify the user’s question into one of the following categories:

1. theory_only – General sustainability concepts, definitions, or methods. These do not refer to specific products, materials, or comparison/evaluation.
   - Examples: What is circularity? What is an EPD? What is LCA? What is a declared unit?

2. comparison_question – Questions that compare or evaluate selected products or indicators.
   - Examples: Why does Product A have a higher GWP than Product B? Are these bricks more circular than those ones?

3. hybrid_theory_comparison – Like comparison_question, but needing theoretical explanation to interpret differences.
   - Examples: Why is the ADP value for Product A higher? Why is the circularity of these tiles questioned?

4. new_product_query – Mentions products not in the current selection, or unknown to the system.
   - Examples: Is straw insulation sustainable? What about using mycelium-based bricks?

5. indicator_explanation – Asks to explain or define a measurable environmental impact indicator (e.g., from LCIA or exchange categories).
   - Examples: What does POCP mean? What is PENRE? What is ADPE?

6. recommendation_query – Asks for the best product or material based on sustainability criteria.
   - Examples: What’s the most circular insulation material? What’s best for low-carbon facades?

7. product_followup – Asks for clarification or explanation about already selected products, without making direct comparisons or asking for recommendations.
   - Examples: Can you explain more about the lifecycle of these doors? What materials are reused in this group?

Respond with only one of the following labels:
theory_only, comparison_question, hybrid_theory_comparison, new_product_query, indicator_explanation, recommendation_query, product_followup

Examples:
Q: What is an EPD?
A: theory_only

Q: Are these products circular?
A: product_followup

Q: What is POCP?
A: indicator_explanation

Q: What’s the most circular roofing material?
A: recommendation_query

Q: Why is the ADPF value for Product A higher?
A: hybrid_theory_comparison

Q: What materials are reused in these selected products?
A: product_followup

Now classify this question:
Q: {question}

A:
""".strip()

    try:
        raw_response = query_llm(classification_prompt)
        label = raw_response.strip().lower()

        valid_labels = {
            "theory_only",
            "comparison_question",
            "hybrid_theory_comparison",
            "new_product_query",
            "indicator_explanation",
            "recommendation_query",
            "product_followup"
        }

        if label in valid_labels:
            return label
        else:
            logger.warning(f"Classifier returned unexpected label: {label}")
            return "unknown"
    except Exception as e:
        logger.exception("Classification failed")
        return "unknown"

def generate_comparison_prompt(document_ids, selected_indicators, max_extra=0, statistics=None):
    """
    Generate a comparison prompt using selected indicators and optional statistical context.
    """
    # Get product info to use names instead of IDs
    product_info = get_product_info(document_ids)
    product_names = {str(product['id']): product['name'] for product in product_info}

    # Get product indicators - only user-selected indicators
    product_indicators = get_product_indicators(document_ids, selected_indicators)

    product_blocks = []
    for pid in document_ids:
        indicators = product_indicators.get(pid, {})
        if not indicators:
            continue

        product_name = product_names.get(pid, f"Product {pid}")
        lines = [f"Product: {product_name}", "Environmental Indicators:"]

        for key in selected_indicators:
            if key in indicators:
                for module, value in indicators[key].get("modules", {}).items():
                    lines.append(f"- {key} ({indicators[key]['unit']}): {module}: {value}")

        product_blocks.append("\n".join(lines))

    # Collect all unique indicator keys
    indicator_keys = set(selected_indicators)

    # Fetch metadata using get_indicator_info
    indicator_descriptions_list = get_indicator_info(list(indicator_keys))
    indicator_descriptions = {item["key"]: item for item in indicator_descriptions_list}

    indicator_info_lines = []
    for key in sorted(indicator_keys):
        meta = indicator_descriptions.get(key)
        if meta:
            name = meta.get("name", "")
            desc = meta.get("short_description", "")
            indicator_info_lines.append(f"- {key}: {name} – {desc}")

    indicator_info_block = "\n".join(indicator_info_lines) if indicator_info_lines else "(No additional indicator information available.)"

    # Optional: Add indicator statistics block
    statistics_block = ""
    if statistics:
        stats_lines = ["Indicator Category Statistics (Same Category):"]
        for key in sorted(statistics):
            for module, values in statistics[key].items():
                mean = values.get("mean")
                min_val = values.get("min")
                max_val = values.get("max")
                unit = values.get("unit", "")
                stats_lines.append(
                    f"- {key} ({unit}) in {module}: mean = {mean}, min = {min_val}, max = {max_val}"
                )
        statistics_block = "\n" + "\n".join(stats_lines)

    module_reference = """
Life Cycle Modules:
- A1-A3: Product stage (raw material extraction, transport, manufacturing)
- A4-A5: Construction stage
- B1-B7: Use stage
- C1-C4: End-of-life stage
- D: Benefits and loads beyond system boundary
    """

    prompt = f"""
You are a sustainability analyst specializing in Environmental Product Declarations (EPDs) for building materials.

Your task is to compare the following products based on their environmental indicator values, with a focus on the user-selected indicators.

CRITICAL COMPARISON RULES:
1. Compare the the indicators accross ALL life cycle modules.
2. Compare ONLY values for the SAME indicator AND the SAME life cycle module.
3. If a value is missing for one product, do NOT compare that indicator/module.
4. Always specify the module when mentioning a value.
5. Compare how each indicator's values fit within the statistical range (mean, min, max) for its category and module.

USER-SELECTED INDICATORS are the primary focus of your comparison.

Products to compare:
----------------------------------------
{"\n\n".join(product_blocks)}
----------------------------------------

Indicator information:
{indicator_info_block}

{statistics_block}

{module_reference.strip()}

Begin your analysis:
"""
    return prompt

# RAG helper functions
def get_theory_chunks(embedding, limit=5):
    """Retrieves theoretical chunks from vector database."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT chunk
                FROM embeddings
                WHERE metadata->>'source' = 'theory'
                ORDER BY embedding <-> %s::vector
                LIMIT %s;
            """, (embedding, limit))
            
            return [row[0] for row in cur.fetchall()]
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.exception("Error retrieving theory chunks")
        return []

def get_epd_chunks(embedding, document_ids=None, limit=5):
    """Retrieves product data chunks from vector database."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            if document_ids:
                # Filter by document IDs
                product_placeholders = ', '.join(['%s'] * len(document_ids))
                cur.execute(f"""
                    SELECT chunk
                    FROM embeddings
                    WHERE process_id IN ({product_placeholders})
                    AND metadata->>'source' = 'epd'
                    ORDER BY embedding <-> %s::vector
                    LIMIT %s;
                """, (*document_ids, embedding, limit))
            else:
                # No filter, get most relevant chunks
                cur.execute("""
                    SELECT chunk
                    FROM embeddings
                    WHERE metadata->>'source' = 'epd'
                    ORDER BY embedding <-> %s::vector
                    LIMIT %s;
                """, (embedding, limit))
                
            return [row[0] for row in cur.fetchall()]
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.exception("Error retrieving EPD chunks")
        return []

def search_epd_by_term(search_term, limit=5):
    """Searches EPD data by text search term."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Basic text search in product names and descriptions
            cur.execute("""
                SELECT process_id, name_en, description_en
                FROM products
                WHERE 
                    name_en ILIKE %s OR
                    description_en ILIKE %s
                LIMIT %s;
            """, (f"%{search_term}%", f"%{search_term}%", limit))
            
            product_ids = [str(row[0]) for row in cur.fetchall()]
            
            if product_ids:
                return get_epd_chunks(None, product_ids, limit)
            return []
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.exception(f"Error searching EPD by term: {search_term}")
        return []

def get_indicator_info(indicator_ids):
    """Retrieves detailed information about indicators."""
    if not indicator_ids:
        return []
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            placeholders = ', '.join(['%s'] * len(indicator_ids))
            cur.execute(f"""
                SELECT 
                    indicator_key, 
                    name, 
                    short_description, 
                    long_description
                FROM indicators
                WHERE indicator_key IN ({placeholders})
            """, tuple(indicator_ids))
            
            indicators = []
            for row in cur.fetchall():
                indicators.append({
                    "key": row[0],
                    "name": row[1],
                    "short_description": row[2],
                    "long_description": row[3]
                })
            return indicators
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.exception("Error retrieving indicator information")
        return []

def get_product_info(document_ids):
    """Retrieves comprehensive information about products with fallbacks for AI-generated content."""
    if not document_ids:
        return []
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            placeholders = ', '.join(['%s'] * len(document_ids))
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
                WHERE process_id IN ({placeholders})
            """, tuple(document_ids))
            
            products = []
            for row in cur.fetchall():
                (process_id, name_en, name_en_ai, description_en, description_en_ai, 
                 short_desc_en_ai, tech_en, tech_en_ai, cat1, cat2, cat3) = row
                
                # Use fallbacks where needed
                name = name_en if name_en else name_en_ai
                description = description_en if description_en else description_en_ai
                tech_description = tech_en if tech_en else tech_en_ai
                
                products.append({
                    "id": str(process_id),
                    "name": name,
                    "description": description,
                    "short_description": short_desc_en_ai,
                    "technical_description": tech_description,
                    "category_level_1": cat1,
                    "category_level_2": cat2,
                    "category_level_3": cat3,
                    # Include original fields for reference
                    "name_en": name_en,
                    "name_en_ai": name_en_ai,
                    "description_en": description_en,
                    "description_en_ai": description_en_ai,
                    "short_desc_en_ai": short_desc_en_ai,
                    "tech_descr_en": tech_en,
                    "tech_descr_en_ai": tech_en_ai
                })
            return products
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.exception("Error retrieving product information")
        return []

def get_combined_indicators(document_ids, selected_indicators, max_extra=3):
    """
    Returns indicators per product: all user-selected ones, plus a few statistically significant extras
    if they are meaningful (non-zero, non-null) and not already selected.
    """
    if not document_ids:
        return {}

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        placeholders = ', '.join(['%s'] * len(document_ids))
        product_indicators = {pid: {} for pid in document_ids}

        # Fetch user-selected indicators first
        if selected_indicators:
            cur.execute(f"""
                SELECT l.process_id, l.indicator_key, l.unit, lm.module, lm.amount
                FROM lcia_results l
                JOIN lcia_moduleamounts lm ON l.lcia_id = lm.lcia_id
                WHERE l.process_id IN ({placeholders})
                AND l.indicator_key IN ({', '.join(['%s'] * len(selected_indicators))})
            """, tuple(document_ids + selected_indicators))

            for row in cur.fetchall():
                pid, key, unit, module, amount = row
                if amount is None:
                    continue
                pid = str(pid)
                if key not in product_indicators[pid]:
                    product_indicators[pid][key] = {"unit": unit, "modules": {}}
                product_indicators[pid][key]["modules"][module] = amount

        # Get category info for statistical comparison
        cur.execute(f"""
            SELECT process_id, category_level_1, category_level_2, category_level_3
            FROM products
            WHERE process_id IN ({placeholders})
        """, tuple(document_ids))

        product_categories = {}
        for row in cur.fetchall():
            pid, cat1, cat2, cat3 = row
            product_categories[str(pid)] = (cat1, cat2, cat3)

        # Fetch all indicators for significance testing
        cur.execute(f"""
            SELECT l.process_id, l.indicator_key, l.unit, lm.module, lm.amount
            FROM lcia_results l
            JOIN lcia_moduleamounts lm ON l.lcia_id = lm.lcia_id
            WHERE l.process_id IN ({placeholders})
        """, tuple(document_ids))

        full_data = {}
        for row in cur.fetchall():
            pid, key, unit, module, amount = row
            pid = str(pid)
            if amount is None or amount == 0:
                continue
            if pid not in full_data:
                full_data[pid] = {}
            if key not in full_data[pid]:
                full_data[pid][key] = {"unit": unit, "modules": {}}
            full_data[pid][key]["modules"][module] = amount

        # Apply significance test (z-score logic)
        for pid, indicators in full_data.items():
            if pid not in product_categories:
                continue
            cat1, cat2, cat3 = product_categories[pid]
            count = 0
            for key, data in indicators.items():
                if key in selected_indicators or key in product_indicators[pid]:
                    continue
                for module, val in data["modules"].items():
                    cur.execute("""
                        SELECT mean, std_dev, min, max
                        FROM indicator_statistics
                        WHERE indicator_key = %s AND module = %s
                        AND category_level_1 = %s AND category_level_2 = %s AND category_level_3 = %s
                    """, (key, module, cat1, cat2, cat3))
                    row = cur.fetchone()
                    if not row:
                        continue
                    mean, std_dev, min_val, max_val = row
                    if mean is None or std_dev is None or std_dev == 0:
                        continue
                    z = abs((val - mean) / std_dev)
                    if z < 1.0:
                        continue

                    # Keep only if we're not over budget
                    if key not in product_indicators[pid]:
                        product_indicators[pid][key] = {"unit": data["unit"], "modules": {}}
                    product_indicators[pid][key]["modules"][module] = val
                    count += 1
                    if count >= max_extra:
                        break

        return product_indicators

    except Exception as e:
        logger.exception("Error in get_combined_indicators")
        return {}
    finally:
        cur.close()
        conn.close()

def get_product_indicators(document_ids, indicator_ids):
    """
    Retrieves product-specific indicator values from LCIA results and exchanges.
    
    Args:
        document_ids: List of product IDs
        indicator_ids: List of indicator keys
        
    Returns:
        Dictionary mapping product IDs to their indicator values
    """
    if not document_ids or not indicator_ids:
        return {}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            product_indicators = {}
            
            # Set up placeholders for SQL query
            product_placeholders = ', '.join(['%s'] * len(document_ids))
            indicator_placeholders = ', '.join(['%s'] * len(indicator_ids))
            
            # Get LCIA results
            cur.execute(f"""
                SELECT l.process_id, l.indicator_key, l.unit, lm.module, lm.amount
                FROM lcia_results l
                JOIN lcia_moduleamounts lm ON l.lcia_id = lm.lcia_id
                WHERE l.process_id IN ({product_placeholders})
                AND l.indicator_key IN ({indicator_placeholders})
            """, tuple(document_ids) + tuple(indicator_ids))
            
            lcia_rows = cur.fetchall()
            
            # Get exchange results
            cur.execute(f"""
                SELECT e.process_id, e.indicator_key, e.unit, em.module, em.amount
                FROM exchanges e
                JOIN exchange_moduleamounts em ON e.exchange_id = em.exchange_id
                WHERE e.process_id IN ({product_placeholders})
                AND e.indicator_key IN ({indicator_placeholders})
            """, tuple(document_ids) + tuple(indicator_ids))
            
            exchange_rows = cur.fetchall()
            
            # Process LCIA results
            for row in lcia_rows:
                process_id, indicator_key, unit, module, amount = row
                process_id = str(process_id)
                
                if process_id not in product_indicators:
                    product_indicators[process_id] = {}
                    
                if indicator_key not in product_indicators[process_id]:
                    product_indicators[process_id][indicator_key] = {
                        "unit": unit,
                        "modules": {}
                    }
                
                if module:
                    product_indicators[process_id][indicator_key]["modules"][module] = amount
            
            # Process exchange results
            for row in exchange_rows:
                process_id, indicator_key, unit, module, amount = row
                process_id = str(process_id)
                
                if process_id not in product_indicators:
                    product_indicators[process_id] = {}
                    
                if indicator_key not in product_indicators[process_id]:
                    product_indicators[process_id][indicator_key] = {
                        "unit": unit,
                        "modules": {}
                    }
                
                if module:
                    product_indicators[process_id][indicator_key]["modules"][module] = amount
            
            return product_indicators
            
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.exception("Error retrieving product-specific indicator values")
        return {}
    
def get_statistically_important_indicators(document_ids, max_indicators=2):
    """
    Retrieves only statistically significant indicator values for specified products.
    Selects indicators that are notably high or low compared to category averages.
    
    Args:
        document_ids: List of product IDs
        max_indicators: Maximum number of indicators to return per product
        
    Returns:
        Dictionary mapping product IDs to their most statistically significant indicator values
    """
    if not document_ids:
        return {}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # First get the product category information
            product_categories = {}
            product_placeholders = ', '.join(['%s'] * len(document_ids))
            cur.execute(f"""
                SELECT 
                    process_id, 
                    category_level_1, 
                    category_level_2, 
                    category_level_3
                FROM products
                WHERE process_id IN ({product_placeholders})
            """, tuple(document_ids))
            
            for row in cur.fetchall():
                process_id, cat1, cat2, cat3 = row
                process_id = str(process_id)
                product_categories[process_id] = {
                    "category_level_1": cat1,
                    "category_level_2": cat2,
                    "category_level_3": cat3
                }
            
            # Get LCIA results and exchange results
            product_indicators = {}
            lcia_results = {}
            
            # Get LCIA results for all indicators
            cur.execute(f"""
                SELECT l.process_id, l.indicator_key, l.unit, lm.module, lm.amount
                FROM lcia_results l
                JOIN lcia_moduleamounts lm ON l.lcia_id = lm.lcia_id
                WHERE l.process_id IN ({product_placeholders})
            """, tuple(document_ids))
            
            for row in cur.fetchall():
                process_id, indicator_key, unit, module, amount = row
                process_id = str(process_id)
                
                if process_id not in lcia_results:
                    lcia_results[process_id] = {}
                
                if indicator_key not in lcia_results[process_id]:
                    lcia_results[process_id][indicator_key] = {
                        "unit": unit,
                        "modules": {}
                    }
                
                if module and amount is not None:
                    lcia_results[process_id][indicator_key]["modules"][module] = amount
            
            # Now get statistics for each indicator to determine significance
            for process_id, indicators in lcia_results.items():
                if process_id not in product_categories:
                    continue
                    
                cat1 = product_categories[process_id]["category_level_1"]
                cat2 = product_categories[process_id]["category_level_2"]
                cat3 = product_categories[process_id]["category_level_3"]
                
                # Process each indicator to calculate its statistical significance
                indicator_significance = []
                
                for indicator_key, data in indicators.items():
                    for module, value in data["modules"].items():
                        # Get statistics for this indicator/module combination
                        cur.execute("""
                            SELECT mean, std_dev, min, max
                            FROM indicator_statistics
                            WHERE indicator_key = %s
                            AND module = %s
                            AND category_level_1 = %s
                            AND category_level_2 = %s
                            AND category_level_3 = %s
                        """, (indicator_key, module, cat1, cat2, cat3))
                        
                        stat_row = cur.fetchone()
                        if stat_row:
                            mean, std_dev, min_val, max_val = stat_row
                            
                            # Skip if statistics are missing
                            if mean is None or std_dev is None or std_dev == 0:
                                continue
                                
                            # Calculate z-score to measure how far from the mean
                            z_score = abs((value - mean) / std_dev) if std_dev > 0 else 0
                            
                            # Calculate percentile position
                            range_size = max_val - min_val if max_val is not None and min_val is not None else 1
                            if range_size > 0:
                                percentile = (value - min_val) / range_size if range_size > 0 else 0.5
                            else:
                                percentile = 0.5
                            
                            # Higher z-score means more statistically significant
                            indicator_significance.append({
                                "indicator_key": indicator_key,
                                "module": module,
                                "value": value,
                                "unit": data["unit"],
                                "z_score": z_score,
                                "percentile": percentile,
                                "is_high": value > mean,
                                "is_low": value < mean
                            })
                
                # Sort by statistical significance (z-score)
                indicator_significance.sort(key=lambda x: x["z_score"], reverse=True)
                
                # Initialize product_indicators for this product
                product_indicators[process_id] = {}
                
                # Take top significant indicators, but try to balance high and low values
                high_indicators = [ind for ind in indicator_significance if ind["is_high"]]
                low_indicators = [ind for ind in indicator_significance if ind["is_low"]]
                
                # Take up to half from high values and half from low values
                half_max = max_indicators // 2
                selected_high = high_indicators[:half_max]
                selected_low = low_indicators[:half_max]
                
                # If we didn't use all slots, fill with the remaining most significant
                remaining_slots = max_indicators - len(selected_high) - len(selected_low)
                if remaining_slots > 0:
                    # Filter out already selected
                    selected_keys = [(ind["indicator_key"], ind["module"]) for ind in selected_high + selected_low]
                    remaining = [
                        ind for ind in indicator_significance 
                        if (ind["indicator_key"], ind["module"]) not in selected_keys
                    ]
                    
                    # Add remaining most significant
                    selected_high.extend(remaining[:remaining_slots])
                
                # Combine and process selected indicators
                selected_indicators = selected_high + selected_low
                
                for ind in selected_indicators:
                    indicator_key = ind["indicator_key"]
                    if indicator_key not in product_indicators[process_id]:
                        product_indicators[process_id][indicator_key] = {
                            "unit": ind["unit"],
                            "modules": {},
                            "significance": {}  # Add significance info
                        }
                    
                    product_indicators[process_id][indicator_key]["modules"][ind["module"]] = ind["value"]
                    product_indicators[process_id][indicator_key]["significance"][ind["module"]] = {
                        "z_score": ind["z_score"],
                        "percentile": ind["percentile"],
                        "is_high": ind["is_high"],
                        "is_low": ind["is_low"]
                    }
            
            # Fetch metadata for included indicators
            all_indicator_keys = set()
            for process_indicators in product_indicators.values():
                all_indicator_keys.update(process_indicators.keys())
            
            if all_indicator_keys:
                indicator_placeholders = ', '.join(['%s'] * len(all_indicator_keys))
                cur.execute(f"""
                    SELECT 
                        indicator_key, 
                        name, 
                        short_description
                    FROM indicators
                    WHERE indicator_key IN ({indicator_placeholders})
                """, tuple(all_indicator_keys))
                
                indicator_metadata = {}
                for row in cur.fetchall():
                    indicator_key, name, short_description = row
                    indicator_metadata[indicator_key] = {
                        "name": name,
                        "short_description": short_description
                    }
                
                # Add metadata to the product indicators
                for process_id in product_indicators:
                    for indicator_key in list(product_indicators[process_id].keys()):
                        if indicator_key in indicator_metadata:
                            product_indicators[process_id][indicator_key]["name"] = indicator_metadata[indicator_key]["name"]
                            product_indicators[process_id][indicator_key]["description"] = indicator_metadata[indicator_key]["short_description"]
            
            return product_indicators
            
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.exception("Error retrieving statistically important indicators")
        return {}
    
# Prompt generation
# Modify the build_specialized_prompt function to include the module integrity warning
def build_specialized_prompt(category, question, chunks_context, product_info=None, indicator_info=None, product_indicators=None):
    """
    Builds a specialized prompt based on question category and available context.
    """
    # Base context
    base_context = chunks_context if chunks_context else "No relevant context found."
    
    # Format product info
    product_context = ""
    if product_info:
        # Create detailed product descriptions with indicator values
        product_details = []
        for p in product_info:
            product_id = p['id']
            product_detail = [
                f"Product: {p['name']}",
                f"  Category: {p['category_level_1']}/{p['category_level_2']}/{p['category_level_3']}",
                f"  Description: {p['description']}",
            ]
            
            # Add technical description if available and not too long
            if p.get('technical_description') and len(p.get('technical_description')) < 250:
                product_detail.append(f"  Technical Description: {p['technical_description']}")
                
            # Add short description if available, different, and not too long
            if (p.get('short_description') and p['short_description'] != p['description'] 
                and len(p.get('short_description')) < 200):
                product_detail.append(f"  Summary: {p['short_description']}")
            
            # Add product-specific indicator values if available
            if product_indicators and product_id in product_indicators:
                product_indicator_values = []
                for indicator_key, data in product_indicators[product_id].items():
                    # Get indicator name from indicator_info if available
                    indicator_name = indicator_key
                    for ind in (indicator_info or []):
                        if ind.get('key') == indicator_key:
                            indicator_name = f"{ind.get('name')} ({indicator_key})"
                            break
                    
                    # Format the module values
                    module_values = []
                    
                    # Check if we have significance data
                    has_significance = "significance" in data
                    
                    for module, value in data.get('modules', {}).items():
                        if value is not None:
                            # Format the value with appropriate precision
                            if isinstance(value, float):
                                if abs(value) < 0.001:
                                    formatted_value = f"{value:.2e}"
                                else:
                                    formatted_value = f"{value:.3f}"
                            else:
                                formatted_value = str(value)
                                
                            # Add significance marker if available
                            if has_significance and module in data.get('significance', {}):
                                sig = data['significance'][module]
                                if sig.get('is_high') and sig.get('z_score', 0) > 1.5:
                                    formatted_value += " (high)"
                                elif sig.get('is_low') and sig.get('z_score', 0) > 1.5:
                                    formatted_value += " (low)"
                                    
                            module_values.append(f"{module}: {formatted_value}")
                    
                    if module_values:
                        product_indicator_values.append(
                            f"    {indicator_name} ({data.get('unit', 'unknown unit')}): " + 
                            ", ".join(module_values)
                        )
                
                if product_indicator_values:
                    product_detail.append("  Notable Indicator Values:")
                    product_detail.extend(product_indicator_values)
            
            product_details.append("\n".join(product_detail))
        
        product_context = f"Selected Products:\n{'-' * 30}\n" + "\n\n".join(product_details) + f"\n{'-' * 30}\n\n"
    
    # Format indicator info
    indicator_context = ""
    if indicator_info:
        indicator_details = []
        for i in indicator_info:
            indicator_detail = [
                f"Indicator {i['key']}: {i['name']}",
                f"  Description: {i['short_description']}",
            ]
            # Only include long description if it's not too verbose
            if i.get('long_description') and len(i.get('long_description')) < 300:
                indicator_detail.append(f"  Detailed Information: {i['long_description']}")
            indicator_details.append("\n".join(indicator_detail))
        
        indicator_context = f"Selected Indicators:\n{'-' * 30}\n" + "\n\n".join(indicator_details) + f"\n{'-' * 30}\n\n"
    
    # Common warning about not inventing data
    no_invention_warning = """IMPORTANT: Only use numerical values explicitly provided above. Do not make up or infer any values not clearly stated in the context. If data is missing, acknowledge this limitation."""
    
    # Module integrity warning (for product-related categories)
    module_integrity_warning = """
CRITICAL INTEGRITY INSTRUCTION: Environmental indicator values are SPECIFIC to their life cycle modules.

- Each value is ONLY valid for its specific module (A1, A1-A3, B1, C4, etc.)
- You must NEVER present a module-specific value (e.g., A1-A3: 25.4) as representing the entire indicator
- When citing values, ALWAYS include the exact module code: "GWP for module A1-A3: 25.4", NOT just "GWP: 25.4"
- Different modules (A1 vs B2 vs C4) represent different life cycle stages and CANNOT be combined or compared directly
- NEVER sum up values across different modules to create a "total" unless explicitly provided
"""

    # Module explanation (for product-related categories)
    module_explanation = """
REFERENCE - Life Cycle Modules:
- A1-A3: Product stage (raw material supply, transport, manufacturing)
- A4-A5: Construction stage (transport to site, installation)
- B1-B7: Use stage (use, maintenance, repair, replacement, etc.)
- C1-C4: End-of-life stage (demolition, transport, waste processing, disposal)
- D: Benefits beyond system boundary (reuse, recovery, recycling potential)
"""
    
    # Determine if this is a product-related category that needs the module warnings
    product_related = category in ["comparison_question", "hybrid_theory_comparison", "product_followup"]
    
    # Product-related templates get the additional warnings
    product_warnings = f"{module_integrity_warning}\n{module_explanation}" if product_related else ""
    
    # Prompt templates by category
    prompt_templates = {
        "theory_only": f"""You are an expert in building materials sustainability and life cycle assessment.

Question: {question}

Context:
{base_context}

{no_invention_warning}

Answer the question clearly, providing definitions and explaining key terminology. Focus on the theoretical concepts requested in the question.

Answer:""",

        "comparison_question": f"""You are a sustainability analyst specializing in Environmental Product Declarations (EPDs).

Question: {question}

{product_context}
{indicator_context}
Context:
{base_context}

{no_invention_warning}

{product_warnings}

Compare the products objectively based on their indicator values. ONLY compare values for the SAME indicator AND SAME module between products (e.g., GWP module A1-A3 from Product 1 vs. GWP module A1-A3 from Product 2).

If two products don't have values for the same modules, clearly state: "A direct comparison for [indicator] cannot be made because the products report values for different life cycle modules."

Answer:""",

        "hybrid_theory_comparison": f"""You are a sustainability educator specializing in building materials and life cycle assessment.

Question: {question}

{product_context}
{indicator_context}
Context:
{base_context}

{no_invention_warning}

{product_warnings}

First explain the relevant sustainability concepts, then analyze the differences between the products' indicator values. ONLY compare values for the SAME indicator AND SAME module between products.

Help the user understand both what the differences are and why they matter from a sustainability perspective.

Answer:""",

        "new_product_query": f"""You are a building materials sustainability expert.

Question: {question}

Context:
{base_context}

{no_invention_warning}

Share what you know about this type of product's environmental performance, sustainability characteristics, and common life cycle considerations based on the information in the context.

Answer:""",

        "indicator_explanation": f"""You are an environmental impact assessment specialist.

Question: {question}

{indicator_context}
Context:
{base_context}

{no_invention_warning}

Explain what this indicator measures, its units, what environmental impacts it relates to, and why it's relevant for building products. Use clear language while maintaining technical accuracy.

Answer:""",

        "recommendation_query": f"""You are a sustainable building materials consultant.

Question: {question}

Context:
{base_context}

{no_invention_warning}

Recommend products or materials that perform well on relevant sustainability criteria based on the information provided. Explain the basis for your recommendations and mention any limitations in the available data.

Answer:""",

        "product_followup": f"""You are a product sustainability analyst specializing in building materials.

Question: {question}

{product_context}
{indicator_context}
Context:
{base_context}

{no_invention_warning}

{product_warnings}

Note: Only statistically significant indicators (those that are notably higher or lower than category averages) are shown for each product.

When discussing the products:
1. ONLY mention numerical values that are EXPLICITLY shown in the product data above
2. ALWAYS specify which module a value belongs to when citing any indicator value
3. NEVER refer to a single module's value as representing the entire indicator
4. If asked about a specific aspect not covered in the data, state clearly that this information isn't provided

Answer:"""
    }
    
    # Use the appropriate template or fall back to a generic one
    default_template = f"""You are a sustainability assistant specializing in building materials.

Question: {question}

{product_context if product_context else ""}
{indicator_context if indicator_context else ""}
Context:
{base_context}

{no_invention_warning}

Answer:"""

    return prompt_templates.get(category, default_template)

@app.post("/compareAnalysis")
async def compare_analysis(data: CompareAnalysisRequest):
    """
    Specialized endpoint for product comparison analysis focusing only on selected indicators
    """
    product_ids = data.productIds
    indicator_ids = data.indicatorIds
    llm_model = data.llmModel

    # Log the request
    logger.info(f"[INFO] Compare analysis request for products: {product_ids}")
    logger.info(f"[INFO] Compare analysis indicators: {indicator_ids}")
    logger.info(f"[INFO] Selected LLM: {llm_model}")

    # Create a log object
    analysis_log = {
        "product_ids": product_ids,
        "indicator_ids": indicator_ids,
        "llm_model": llm_model,
        "prompt": None,
        "response": None,
        "error": None
    }

    # Input validation
    if not product_ids or len(product_ids) < 1:
        error_msg = "At least one product must be selected for analysis."
        analysis_log["error"] = error_msg
        query_logger.log_query(analysis_log)
        return JSONResponse(
            status_code=400,
            content={"answer": error_msg}
        )

    if not indicator_ids:
        error_msg = "At least one indicator must be selected for analysis."
        analysis_log["error"] = error_msg
        query_logger.log_query(analysis_log)
        return JSONResponse(
            status_code=400,
            content={"answer": error_msg}
        )

    try:
        # Get product info
        product_info = get_product_info(product_ids)
        if not product_info:
            error_msg = "Could not retrieve product information."
            analysis_log["error"] = error_msg
            query_logger.log_query(analysis_log)
            return JSONResponse(
                status_code=404,
                content={"answer": error_msg}
            )

        # Get indicator information
        indicator_info = get_indicator_info(indicator_ids)

        # Get indicator values (only for selected indicators)
        product_indicators = get_product_indicators(product_ids, indicator_ids)

        # Gather all used modules
        module_names = sorted({
            module
            for indicators in product_indicators.values()
            for ind in indicators.values()
            for module in ind.get("modules", {})
        })

        # Determine category from first product
        cat1 = product_info[0]["category_level_1"]
        cat2 = product_info[0]["category_level_2"]
        cat3 = product_info[0]["category_level_3"]

        # Fetch statistics for selected indicators + modules + category
        stats_rows = []
        if module_names:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                try:
                    stats_indicator_placeholders = ', '.join(['%s'] * len(indicator_ids))
                    stats_module_placeholders = ', '.join(['%s'] * len(module_names))

                    cur.execute(f"""
                        SELECT indicator_key, module, mean, min, max, unit
                        FROM indicator_statistics
                        WHERE indicator_key IN ({stats_indicator_placeholders})
                        AND module IN ({stats_module_placeholders})
                        AND category_level_1 = %s
                        AND category_level_2 = %s
                        AND category_level_3 = %s
                    """, tuple(indicator_ids) + tuple(module_names) + (cat1, cat2, cat3))

                    stats_rows = cur.fetchall()
                    logger.info(f"Fetched {len(stats_rows)} statistics rows")
                finally:
                    cur.close()
                    conn.close()
            except Exception as e:
                logger.exception("Failed to fetch indicator statistics")

        # Convert stats to a dict for use in prompt
        indicator_statistics = {}
        for row in stats_rows:
            key, module, mean, min_val, max_val, unit = row
            if key not in indicator_statistics:
                indicator_statistics[key] = {}
            indicator_statistics[key][module] = {
                "mean": mean,
                "min": min_val,
                "max": max_val,
                "unit": unit
            }

        # Generate prompt (with selected indicators only, no statistical extras)
        prompt = generate_comparison_prompt(
            document_ids=product_ids,
            selected_indicators=indicator_ids,
            max_extra=0,
            statistics=indicator_statistics
        )
        analysis_log["prompt"] = prompt

        # Call the LLM
        answer = query_llm(prompt, model_name=llm_model)
        analysis_log["response"] = answer

        # Log the successful query
        log_path = query_logger.log_query(analysis_log)
        logger.info(f"Comparison analysis log saved to {log_path}")

        return JSONResponse(content={"answer": answer})

    except Exception as e:
        error_msg = f"Error during comparison analysis: {str(e)}"
        analysis_log["error"] = error_msg
        query_logger.log_query(analysis_log)
        logger.exception(error_msg)
        return JSONResponse(
            status_code=500,
            content={"answer": "An error occurred during comparison analysis."}
        )

    
@app.post("/askrag")
async def ask_question(data: QuestionRequest):
    """RAG-enhanced question answering endpoint with detailed logging"""
    question = data.question.strip()
    document_ids = data.documentIds or []
    indicator_ids = data.indicatorIds or []
    llm_model = data.llmModel
    
    # Create a query log object to track all steps
    query_log = {
        "question": question,
        "document_ids": document_ids,
        "indicator_ids": indicator_ids,
        "llm_model": llm_model,
        "theory_chunks": [],
        "epd_chunks": [],
        "sql_queries": {},
        "classification": None,
        "prompt": None,
        "response": None,
        "error": None
    }
    
    # Input validation
    if not question:
        error_msg = "Question cannot be empty."
        query_log["error"] = error_msg
        query_logger.log_query(query_log)
        return JSONResponse(
            status_code=400,
            content={"answer": error_msg}
        )
    
    logger.info(f"[INFO] Question received: {question}")
    logger.info(f"[INFO] Selected LLM: {llm_model}")
    if document_ids:
        logger.info(f"[INFO] Selected products: {document_ids}")
    if indicator_ids:
        logger.info(f"[INFO] Selected indicators: {indicator_ids}")

    # Check if embedding model is available
    if embedding_model is None:
        error_msg = "Embedding model is not available. Please try again later."
        query_log["error"] = error_msg
        query_logger.log_query(query_log)
        return JSONResponse(
            status_code=503,
            content={"answer": error_msg}
        )

    # Step 1: Classify the question
    try:
        category = classify_question(question)
        query_log["classification"] = category
        logger.info(f"[INFO] Classified question as: {category}")
    except Exception as e:
        error_msg = f"Failed to classify question: {str(e)}"
        query_log["error"] = error_msg
        query_logger.log_query(query_log)
        logger.exception(error_msg)
        return JSONResponse(
            status_code=500,
            content={"answer": "An error occurred processing your question."}
        )

    # Step 2: Create embedding
    try:
        embedding = embedding_model.encode(question).tolist()
    except Exception as e:
        error_msg = f"Error during embedding: {str(e)}"
        query_log["error"] = error_msg
        query_logger.log_query(query_log)
        logger.exception(error_msg)
        return JSONResponse(
            status_code=500,
            content={"answer": f"Failed to process your question: {str(e)}"}
        )

    # Step 3: Retrieve relevant context based on question category
    chunks = []
    product_info = None
    indicator_info = None
    product_indicators = None
    
    try:
        # Retrieve different data based on question category
        if category == "theory_only":
            # Only retrieve theory chunks
            theory_sql = """
                SELECT chunk
                FROM embeddings
                WHERE metadata->>'source' = 'theory'
                ORDER BY embedding <-> $1::vector
                LIMIT $2;
            """
            query_log["sql_queries"]["theory"] = theory_sql
            
            theory_chunks = get_theory_chunks(embedding, limit=5)
            query_log["theory_chunks"] = theory_chunks
            chunks.extend(theory_chunks)
            logger.info(f"Retrieved {len(theory_chunks)} theory chunks for theory_only")
            
        elif category == "comparison_question":
            # Retrieve product data and indicator info for comparisons
            if document_ids:
                product_placeholders = ', '.join(['%s'] * len(document_ids))
                epd_sql = f"""
                    SELECT chunk
                    FROM embeddings
                    WHERE process_id IN ({product_placeholders})
                    AND metadata->>'source' = 'epd'
                    ORDER BY embedding <-> %s::vector
                    LIMIT %s;
                """
                query_log["sql_queries"]["epd"] = epd_sql
                
                epd_chunks = get_epd_chunks(embedding, document_ids, limit=5)
                query_log["epd_chunks"] = epd_chunks
                chunks.extend(epd_chunks)
                logger.info(f"Retrieved {len(epd_chunks)} EPD chunks for comparison_question")
                
                # Get enhanced product info
                product_info = get_product_info(document_ids)
                query_log["product_info"] = product_info
                
                # Get product-specific indicator values
                if indicator_ids:
                    product_indicators = get_product_indicators(document_ids, indicator_ids)
                    query_log["product_indicators"] = product_indicators
            
            if indicator_ids:
                indicator_info = get_indicator_info(indicator_ids)
                query_log["indicator_info"] = indicator_info
            
        elif category == "hybrid_theory_comparison":
            # Get both theoretical and product data
            theory_sql = """
                SELECT chunk
                FROM embeddings
                WHERE metadata->>'source' = 'theory'
                ORDER BY embedding <-> $1::vector
                LIMIT $2;
            """
            query_log["sql_queries"]["theory"] = theory_sql
            
            theory_chunks = get_theory_chunks(embedding, limit=3)
            query_log["theory_chunks"] = theory_chunks
            chunks.extend(theory_chunks)
            logger.info(f"Retrieved {len(theory_chunks)} theory chunks for hybrid_theory_comparison")
            
            if document_ids:
                product_placeholders = ', '.join(['%s'] * len(document_ids))
                epd_sql = f"""
                    SELECT chunk
                    FROM embeddings
                    WHERE process_id IN ({product_placeholders})
                    AND metadata->>'source' = 'epd'
                    ORDER BY embedding <-> %s::vector
                    LIMIT %s;
                """
                query_log["sql_queries"]["epd"] = epd_sql
                
                epd_chunks = get_epd_chunks(embedding, document_ids, limit=3)
                query_log["epd_chunks"] = epd_chunks
                chunks.extend(epd_chunks)
                logger.info(f"Retrieved {len(epd_chunks)} EPD chunks for hybrid_theory_comparison")
                
                # Get enhanced product info
                product_info = get_product_info(document_ids)
                query_log["product_info"] = product_info
                
                # Get product-specific indicator values
                if indicator_ids:
                    product_indicators = get_product_indicators(document_ids, indicator_ids)
                    query_log["product_indicators"] = product_indicators
                
            if indicator_ids:
                indicator_info = get_indicator_info(indicator_ids)
                query_log["indicator_info"] = indicator_info
            
        elif category == "new_product_query":
            # Get theory and search for similar products
            theory_sql = """
                SELECT chunk
                FROM embeddings
                WHERE metadata->>'source' = 'theory'
                ORDER BY embedding <-> $1::vector
                LIMIT $2;
            """
            query_log["sql_queries"]["theory"] = theory_sql
            
            theory_chunks = get_theory_chunks(embedding, limit=3)
            query_log["theory_chunks"] = theory_chunks
            chunks.extend(theory_chunks)
            logger.info(f"Retrieved {len(theory_chunks)} theory chunks for new_product_query")
            
            # Extract product terms from question for search
            words = question.lower().split()
            common_building_terms = ["insulation", "brick", "concrete", "wood", "timber", "glass", 
                                    "steel", "aluminum", "roof", "tile", "panel", "facade", "window"]
            search_terms = [word for word in words if word in common_building_terms]
            
            if search_terms:
                query_log["search_terms"] = search_terms
                for term in search_terms[:2]:  # Limit to 2 search terms
                    similar_product_chunks = search_epd_by_term(term, limit=2)
                    query_log["epd_chunks_search"] = similar_product_chunks
                    chunks.extend(similar_product_chunks)
                    logger.info(f"Retrieved {len(similar_product_chunks)} product chunks for search term '{term}'")
            
        elif category == "indicator_explanation":
            # Get theory chunks about indicators
            theory_sql = """
                SELECT chunk
                FROM embeddings
                WHERE metadata->>'source' = 'theory'
                ORDER BY embedding <-> $1::vector
                LIMIT $2;
            """
            query_log["sql_queries"]["theory"] = theory_sql
            
            theory_chunks = get_theory_chunks(embedding, limit=5)
            query_log["theory_chunks"] = theory_chunks
            chunks.extend(theory_chunks)
            logger.info(f"Retrieved {len(theory_chunks)} theory chunks for indicator_explanation")
            
            # If specific indicators are selected, get their info
            if indicator_ids:
                indicator_info = get_indicator_info(indicator_ids)
                query_log["indicator_info"] = indicator_info
            
        elif category == "recommendation_query":
            # Get theory and wide search in product database
            theory_sql = """
                SELECT chunk
                FROM embeddings
                WHERE metadata->>'source' = 'theory'
                ORDER BY embedding <-> $1::vector
                LIMIT $2;
            """
            query_log["sql_queries"]["theory"] = theory_sql
            
            theory_chunks = get_theory_chunks(embedding, limit=2)
            query_log["theory_chunks"] = theory_chunks
            chunks.extend(theory_chunks)
            logger.info(f"Retrieved {len(theory_chunks)} theory chunks for recommendation_query")
            
            # Get diverse product examples from database
            epd_sql = """
                SELECT chunk
                FROM embeddings
                WHERE metadata->>'source' = 'epd'
                ORDER BY embedding <-> $1::vector
                LIMIT $2;
            """
            query_log["sql_queries"]["epd"] = epd_sql
            
            diverse_chunks = get_epd_chunks(embedding, limit=5)
            query_log["epd_chunks"] = diverse_chunks
            chunks.extend(diverse_chunks)
            logger.info(f"Retrieved {len(diverse_chunks)} diverse EPD chunks for recommendation")
            
        elif category == "product_followup":
            # Get information on selected products
            if document_ids:
                product_placeholders = ', '.join(['%s'] * len(document_ids))
                epd_sql = f"""
                    SELECT chunk
                    FROM embeddings
                    WHERE process_id IN ({product_placeholders})
                    AND metadata->>'source' = 'epd'
                    ORDER BY embedding <-> %s::vector
                    LIMIT %s;
                """
                query_log["sql_queries"]["epd"] = epd_sql
                
                epd_chunks = get_epd_chunks(embedding, document_ids, limit=5)
                query_log["epd_chunks"] = epd_chunks
                chunks.extend(epd_chunks)
                logger.info(f"Retrieved {len(epd_chunks)} EPD chunks for product_followup")
                
                # Get enhanced product info
                product_info = get_product_info(document_ids)
                query_log["product_info"] = product_info
                
                # Get statistically significant indicators (outliers compared to category averages)
                product_indicators = get_statistically_important_indicators(document_ids, max_indicators=8)
                query_log["product_indicators"] = product_indicators
                
                # Get indicator counts for logging
                indicator_counts = {product_id: len(indicators) for product_id, indicators in product_indicators.items()}
                logger.info(f"Retrieved statistical outlier indicators for {len(product_indicators)} products")
                logger.info(f"Indicator counts per product: {indicator_counts}")
            
            # Still get specific indicator info if selected
            if indicator_ids:
                indicator_info = get_indicator_info(indicator_ids)
                query_log["indicator_info"] = indicator_info
                
            # Add theory if needed
            if len(chunks) < 3:
                theory_chunks = get_theory_chunks(embedding, limit=2)
                query_log["theory_chunks"] = theory_chunks
                chunks.extend(theory_chunks)
                logger.info(f"Added {len(theory_chunks)} theory chunks to supplement product_followup")
        
        else:  # Unknown category
            # Default approach: get both theory and product data if available
            theory_sql = """
                SELECT chunk
                FROM embeddings
                WHERE metadata->>'source' = 'theory'
                ORDER BY embedding <-> $1::vector
                LIMIT $2;
            """
            query_log["sql_queries"]["theory"] = theory_sql
            
            theory_chunks = get_theory_chunks(embedding, limit=3)
            query_log["theory_chunks"] = theory_chunks
            chunks.extend(theory_chunks)
            logger.info(f"Retrieved {len(theory_chunks)} theory chunks for unknown category")
            
            if document_ids:
                product_placeholders = ', '.join(['%s'] * len(document_ids))
                epd_sql = f"""
                    SELECT chunk
                    FROM embeddings
                    WHERE process_id IN ({product_placeholders})
                    AND metadata->>'source' = 'epd'
                    ORDER BY embedding <-> %s::vector
                    LIMIT %s;
                """
                query_log["sql_queries"]["epd"] = epd_sql
                
                epd_chunks = get_epd_chunks(embedding, document_ids, limit=3)
                query_log["epd_chunks"] = epd_chunks
                chunks.extend(epd_chunks)
                logger.info(f"Retrieved {len(epd_chunks)} EPD chunks for unknown category")
                
                # Get enhanced product info
                product_info = get_product_info(document_ids)
                query_log["product_info"] = product_info
                
                # Get product-specific indicator values
                if indicator_ids:
                    product_indicators = get_product_indicators(document_ids, indicator_ids)
                    query_log["product_indicators"] = product_indicators
                
            if indicator_ids:
                indicator_info = get_indicator_info(indicator_ids)
                query_log["indicator_info"] = indicator_info
        
        # If we didn't get any chunks, try a broader approach
        if not chunks:
            logger.warning("No chunks retrieved with specialized approach, falling back to general retrieval")
            
            theory_sql = """
                SELECT chunk
                FROM embeddings
                WHERE metadata->>'source' = 'theory'
                ORDER BY embedding <-> $1::vector
                LIMIT $2;
            """
            query_log["sql_queries"]["fallback_theory"] = theory_sql
            
            theory_chunks = get_theory_chunks(embedding, limit=2)
            query_log["fallback_theory_chunks"] = theory_chunks
            chunks.extend(theory_chunks)
            
            epd_sql = """
                SELECT chunk
                FROM embeddings
                WHERE metadata->>'source' = 'epd'
                ORDER BY embedding <-> $1::vector
                LIMIT $2;
            """
            query_log["sql_queries"]["fallback_epd"] = epd_sql
            
            general_chunks = get_epd_chunks(embedding, limit=3)
            query_log["fallback_epd_chunks"] = general_chunks
            chunks.extend(general_chunks)
        
        # Debug: Write chunks to file
        working_directory = os.getcwd()
        file_path = os.path.join(working_directory, "fetched_chunks.txt")
        with open(file_path, "w") as file:
            for chunk in chunks:
                file.write(f"{chunk}\n\n")
            
        logger.info(f"Chunks saved to: {file_path}")
        
        if not chunks:
            no_chunks_msg = "I couldn't find relevant information to answer your question. Try a different question or select different products."
            query_log["error"] = "No relevant chunks found"
            query_logger.log_query(query_log)
            logger.warning("No relevant chunks found.")
            return JSONResponse(
                content={"answer": no_chunks_msg}
            )

        logger.info(f"Retrieved a total of {len(chunks)} chunks")
    
    except Exception as e:
        error_msg = f"An error occurred while retrieving context: {str(e)}"
        query_log["error"] = error_msg
        query_logger.log_query(query_log)
        logger.exception(error_msg)
        return JSONResponse(
            status_code=500,
            content={"answer": error_msg}
        )

    # Step 4: Build specialized prompt based on question category
    chunks_context = "\n\n".join(chunks)
    prompt = build_specialized_prompt(category, question, chunks_context, product_info, indicator_info, product_indicators)
    query_log["prompt"] = prompt
    
    logger.info("Prompt constructed. Sending to inference...")

    # Step 5: Send prompt to LLM
    try:
        answer = query_llm(prompt, model_name=llm_model)
        query_log["response"] = answer
        
        if not answer or not isinstance(answer, str):
            error_msg = "LLM returned invalid answer"
            query_log["error"] = error_msg
            query_logger.log_query(query_log)
            logger.warning(f"{error_msg}: {answer}")
            return JSONResponse(
                content={"answer": "I'm sorry, I couldn't generate a proper response. Please try again."}
            )
            
        # Log the successful query
        log_path = query_logger.log_query(query_log)
        logger.info(f"Query log saved to {log_path}")
        
        logger.info("LLM returned result.")
        return JSONResponse(content={"answer": answer})
    except Exception as e:
        error_msg = f"I'm sorry, I'm having trouble generating a response right now. Please try again later. (Error: {str(e)})"
        query_log["error"] = str(e)
        query_logger.log_query(query_log)
        logger.exception("Inference failed")
        return JSONResponse(
            status_code=503,
            content={"answer": error_msg}
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

def get_all_product_indicators(document_ids):
    """
    Retrieves ALL indicator values for specified products, not limited to selected indicators.
    
    Args:
        document_ids: List of product IDs
        
    Returns:
        Dictionary mapping product IDs to all their indicator values
    """
    if not document_ids:
        return {}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            product_indicators = {}
            
            # Set up placeholders for SQL query
            product_placeholders = ', '.join(['%s'] * len(document_ids))
            
            # Get LCIA results for all indicators
            cur.execute(f"""
                SELECT l.process_id, l.indicator_key, l.unit, lm.module, lm.amount
                FROM lcia_results l
                JOIN lcia_moduleamounts lm ON l.lcia_id = lm.lcia_id
                WHERE l.process_id IN ({product_placeholders})
            """, tuple(document_ids))
            
            lcia_rows = cur.fetchall()
            
            # Get exchange results for all indicators
            cur.execute(f"""
                SELECT e.process_id, e.indicator_key, e.unit, em.module, em.amount
                FROM exchanges e
                JOIN exchange_moduleamounts em ON e.exchange_id = em.exchange_id
                WHERE e.process_id IN ({product_placeholders})
            """, tuple(document_ids))
            
            exchange_rows = cur.fetchall()
            
            # Collect all unique indicator keys to fetch their metadata later
            all_indicator_keys = set()
            
            # Process LCIA results
            for row in lcia_rows:
                process_id, indicator_key, unit, module, amount = row
                process_id = str(process_id)
                all_indicator_keys.add(indicator_key)
                
                if process_id not in product_indicators:
                    product_indicators[process_id] = {}
                    
                if indicator_key not in product_indicators[process_id]:
                    product_indicators[process_id][indicator_key] = {
                        "unit": unit,
                        "modules": {}
                    }
                
                if module:
                    product_indicators[process_id][indicator_key]["modules"][module] = amount
            
            # Process exchange results
            for row in exchange_rows:
                process_id, indicator_key, unit, module, amount = row
                process_id = str(process_id)
                all_indicator_keys.add(indicator_key)
                
                if process_id not in product_indicators:
                    product_indicators[process_id] = {}
                    
                if indicator_key not in product_indicators[process_id]:
                    product_indicators[process_id][indicator_key] = {
                        "unit": unit,
                        "modules": {}
                    }
                
                if module:
                    product_indicators[process_id][indicator_key]["modules"][module] = amount
            
            # Fetch metadata for all indicators 
            if all_indicator_keys:
                indicator_placeholders = ', '.join(['%s'] * len(all_indicator_keys))
                cur.execute(f"""
                    SELECT 
                        indicator_key, 
                        name, 
                        short_description
                    FROM indicators
                    WHERE indicator_key IN ({indicator_placeholders})
                """, tuple(all_indicator_keys))
                
                indicator_metadata = {}
                for row in cur.fetchall():
                    indicator_key, name, short_description = row
                    indicator_metadata[indicator_key] = {
                        "name": name,
                        "short_description": short_description
                    }
                
                # Add metadata to the product indicators
                for process_id in product_indicators:
                    for indicator_key in product_indicators[process_id]:
                        if indicator_key in indicator_metadata:
                            product_indicators[process_id][indicator_key]["name"] = indicator_metadata[indicator_key]["name"]
                            product_indicators[process_id][indicator_key]["description"] = indicator_metadata[indicator_key]["short_description"]
            
            return product_indicators
            
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.exception("Error retrieving all product indicator values")
        return {}
    
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