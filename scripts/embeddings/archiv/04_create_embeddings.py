from sentence_transformers import SentenceTransformer
from collections import defaultdict
import psycopg2
import textwrap
import os
from dotenv import load_dotenv
from psycopg2.extras import Json
from psycopg2.extras import execute_values
from tqdm import tqdm
import logging

# Load .env for DB credentials
load_dotenv()

DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

CHUNK_CHAR_LIMIT = 1500
EMBEDDING_DIM = 384  # For bge-small-en-v1.5
model = SentenceTransformer("BAAI/bge-small-en-v1.5")
# EMBEDDING_DIM = 1024  # For bge-large-en-v1.5
# model = SentenceTransformer("BAAI/bge-large-en-v1.5")

def connect():
    return psycopg2.connect(**DB_PARAMS)

def fetch_product_metadata():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.process_id, p.uuid, p.name_en, p.description_en, p.reference_year,
               p.geo_location, p.geo_descr_en, p.tech_descr_en, p.tech_applic_en,
               p.time_repr_en, p.use_advice_de, p.use_advice_en,
               p.generator_de, p.generator_en,
               p.entry_by_de, p.entry_by_en,
               p.admin_version, p.license_type,
               p.access_de, p.access_en,
               p.timestamp, p.formats,
               c.name AS classification_name, c.level AS classification_level,
               c.classId AS classification_class_id, c.classification AS classification_classification
        FROM products p
        LEFT JOIN classifications c ON p.process_id = c.process_id
        LIMIT 10
    """)
    rows = cur.fetchall()
    conn.close()

    metadata = defaultdict(lambda: {
        "uuid": "", "name": "", "desc": "", "year": "",
        "geo": "", "geo_descr": "", "tech_descr": "", "tech_applic": "",
        "time_repr": "", "use_advice_de": "", "use_advice_en": "",
        "generator_de": "", "generator_en": "",
        "entry_by_de": "", "entry_by_en": "",
        "admin_version": "", "license_type": "",
        "access_de": "", "access_en": "",
        "timestamp": "", "formats": "",
        "classifications": []
    })

    for row in rows:
        (
            process_id, uuid, name, desc, year,
            geo, geo_descr, tech_descr, tech_applic, time_repr,
            use_advice_de, use_advice_en,
            generator_de, generator_en,
            entry_by_de, entry_by_en,
            admin_version, license_type,
            access_de, access_en,
            timestamp, formats,
            classification_name, classification_level, classification_class_id, classification_classification,
         ) = row

        entry = metadata[process_id]
        entry.update({
            "uuid": uuid,
            "name": name,
            "desc": desc,
            "year": year,
            "geo": geo,
            "geo_descr": geo_descr,
            "tech_descr": tech_descr,
            "tech_applic": tech_applic,
            "time_repr": time_repr,
            "use_advice_de": use_advice_de,
            "use_advice_en": use_advice_en,
            "generator_de": generator_de,
            "generator_en": generator_en,
            "entry_by_de": entry_by_de,
            "entry_by_en": entry_by_en,
            "admin_version": admin_version,
            "license_type": license_type,
            "access_de": access_de,
            "access_en": access_en,
            "timestamp": str(timestamp) if timestamp else "",
            "formats": formats
        })

        if classification_name or classification_level or classification_class_id or classification_classification:
            entry["classifications"].append({
                "name": classification_name,
                "level": classification_level,
                "classId": classification_class_id,
                "classification": classification_classification
            })

    return metadata

def sql_in_clause(ids):
    return ','.join(['%s'] * len(ids)), tuple(ids)

def fetch_lcia(pids):
    if not pids:
        return defaultdict(list)
    
    conn = connect()
    cur = conn.cursor()
    placeholders, args = sql_in_clause(pids)
    query = f"""
        SELECT l.process_id, l.method_en, l.method_de, l.indicator_key, l.meanamount, l.unit,
               lma.module, lma.scenario, lma.amount
        FROM lcia_results l
        LEFT JOIN lcia_moduleamounts lma ON l.lcia_id = lma.lcia_id
        WHERE l.process_id IN ({placeholders})
    """
    cur.execute(query, args)
    lcia = defaultdict(list)
    for row in cur.fetchall():
        pid, method_en, method_de, ind_k, mean_amt, unit, module, mod_sce, mod_amt = row
        lcia[pid].append({
            "method_en": method_en,
            "method_de": method_de,
            "indicator_key": ind_k,
            "meanamount": mean_amt,
            "unit": unit,
            "module": module,
            "scenario": mod_sce,
            "amount": mod_amt
        })
    cur.close()
    conn.close()
    return lcia

def fetch_exchanges(pids):
    if not pids:
        return defaultdict(list)
    
    conn = connect()
    cur = conn.cursor()
    placeholders, args = sql_in_clause(pids)
    query = f"""
        SELECT e.process_id, e.direction, e.flow_en, e.flow_de, e.indicator_key, e.meanamount, e.unit,
               ema.module, ema.scenario, ema.amount
        FROM exchanges e
        LEFT JOIN exchange_moduleamounts ema ON e.exchange_id = ema.exchange_id
        WHERE e.process_id IN ({placeholders})
    """
    cur.execute(query, args)
    exchanges = defaultdict(list)
    for row in cur.fetchall():
        pid, direction, flow_en, flow_de, indicator_key, meanamount, unit, module, scenario, amount = row
        exchanges[pid].append({
            "direction": direction,
            "flow_en": flow_en,
            "flow_de": flow_de,
            "indicator_key": indicator_key,
            "meanamount": meanamount,
            "unit": unit,
            "module": module,
            "scenario": scenario,
            "amount": amount
        })
    cur.close()
    conn.close()
    return exchanges

def fetch_compliances(pids):
    if not pids:
        return defaultdict(list)
    
    conn = connect()
    cur = conn.cursor()
    placeholders = ','.join(['%s'] * len(pids))
    query = f"""
        SELECT process_id, system_en, approval
        FROM compliances
        WHERE process_id IN ({placeholders})
    """
    cur.execute(query, tuple(pids))
    rows = cur.fetchall()
    conn.close()

    compliances = defaultdict(list)
    for pid, system, approval in rows:
        compliances[pid].append(f"{system or 'Unknown system'} - {approval or 'Unknown approval'}")
    return compliances

def fetch_reviews(pids):
    if not pids:
        return defaultdict(list)
    
    conn = connect()
    cur = conn.cursor()
    placeholders = ','.join(['%s'] * len(pids))
    query = f"""
        SELECT process_id, reviewer, detail_en
        FROM reviews
        WHERE process_id IN ({placeholders})
    """
    cur.execute(query, tuple(pids))
    rows = cur.fetchall()
    conn.close()

    reviews = defaultdict(list)
    for pid, reviewer, detail in rows:
        reviews[pid].append(f"{reviewer or 'Unknown reviewer'}: {detail or 'No detail'}")
    return reviews

def fetch_materials(pids):
    """Fetch materials for the given process IDs."""
    if not pids:
        return defaultdict(list)

    conn = connect()
    cur = conn.cursor()

    # Prepare the SQL query with placeholders for process IDs
    placeholders, args = sql_in_clause(pids)
    query = f"""
        SELECT process_id, property_id, property_name, value, units, description
        FROM materials
        WHERE process_id IN ({placeholders})
    """
    cur.execute(query, args)

    # Organize the results into a dictionary
    materials = defaultdict(list)
    for row in cur.fetchall():
        process_id, property_id, property_name, value, units, description = row
        materials[process_id].append({
            "property_id": property_id,
            "property_name": property_name,
            "value": value,
            "units": units,
            "description": description
        })

    cur.close()
    conn.close()
    return materials

def split_text_to_chunks(text, chunk_size):
    return textwrap.wrap(text, chunk_size, break_long_words=False, replace_whitespace=False)

def generate_structured_chunks():
    metadata = fetch_product_metadata()
    exchanges = fetch_exchanges(metadata.keys())
    lcia = fetch_lcia(metadata.keys())
    compliances = fetch_compliances(metadata.keys())
    reviews = fetch_reviews(metadata.keys())
    materials = fetch_materials(metadata.keys())

    chunks = {}

    for pid in metadata:
        m = metadata[pid]
        m["materials"] = materials.get(pid, [])  # Add materials to metadata

        # Step 1: Basic Info
        basic_text = f"""Product: {m['name']}
                         Year: {m['year']}
                         Description: {m['desc']}
                         
                         Classifications: {', '.join([f"level: {classification['level']} classification: {classification['classification']}" for classification in m['classifications'] if 'name' in classification and 'level' in classification and 'classification' in classification])}
                 
                         Geo: {m['geo']} - {m['geo_descr']}
                         Technical Description: {m['tech_descr']}
                         Technical Application: {m['tech_applic']}
                         Time Representation: {m['time_repr']}
             
                         Use Advice (EN): {m['use_advice_en']}
                         Use Advice (DE): {m['use_advice_de']}
             
                         Generator (EN): {m['generator_en']}
                         Generator (DE): {m['generator_de']}
                         Entry By (EN): {m['entry_by_en']}
                         Entry By (DE): {m['entry_by_de']}
                         Admin Version: {m['admin_version']}
                         License Type: {m['license_type']}
                         Access (EN): {m['access_en']}
                         Access (DE): {m['access_de']}
                         Timestamp: {m['timestamp']}
                         Formats: {m['formats']}
             
                         Material properties:
                         {chr(10).join([f"Name: {material['property_name']}, Value: {material['value']}, Units: {material['units']}, Description: {material['description']}" for material in m.get('materials', [])])}

                         Compliances:
                         {chr(10).join(compliances.get(pid, []))}
             
                         Reviews:
                         {chr(10).join(reviews.get(pid, []))}
                         """
        for i, chunk in enumerate(textwrap.wrap(basic_text.strip(), CHUNK_CHAR_LIMIT)):
            chunk_id = f"{pid}_basic_info_{i}"
            chunks[chunk_id] = {
                "process_id": pid,
                "chunk": chunk,
                "metadata": {
                    "chunk_type": "basic_info",
                    "product_id": pid,
                    "product_name": m["name"],
                    "uuid": m["uuid"]
                }
            }

        # Step 2: LCIA chunks
        lcia_lines = []
        for entry in lcia.get(pid, []):
            method_en = entry["method_en"]
            method_de = entry["method_de"]
            indicator_key = entry["indicator_key"]
            mean_amount = entry["meanamount"]
            unit = entry["unit"]
            module = entry["module"]
            scenario = entry["scenario"]
            amount = entry["amount"]
            line = f"{method_en} {method_de} ({indicator_key}) = {module} {scenario } {amount} {unit}"
            lcia_lines.append(line)

        if lcia_lines:
            lcia_text = f"Product: {m['name']} ({m['uuid']})\nLCIA Data:\n" + "\n".join(lcia_lines)
            for i, chunk in enumerate(textwrap.wrap(lcia_text.strip(), CHUNK_CHAR_LIMIT)):
                chunk_id = f"{pid}_lcia_aggregated_{i}"
                chunks[chunk_id] = {
                    "process_id": pid,
                    "chunk": chunk,
                    "metadata": {
                        "chunk_type": "lcia",
                        "product_id": pid,
                        "product_name": m["name"],
                        "uuid": m["uuid"]
                    }
                }

        # Step 2: Exchanges chunks
        exchange_lines = []
        for entry in exchanges.get(pid, []):
            direction = entry["direction"]
            flow_en = entry["flow_en"]
            flow_de = entry["flow_de"]
            indicator_key = entry["indicator_key"]
            mean_amount = entry["meanamount"]
            unit = entry["unit"]
            module = entry["module"]
            scenario = entry["scenario"]
            amount = entry["amount"]
            line = f"{direction} - {flow_en} {flow_de} {indicator_key}= {module} {scenario } {amount} {unit}"
            exchange_lines.append(line)

        if exchange_lines:
            exchange_text = f"Product: {m['name']} ({m['uuid']})\nExchanges:\n" + "\n".join(exchange_lines)
            for i, chunk in enumerate(textwrap.wrap(exchange_text.strip(), CHUNK_CHAR_LIMIT)):
                chunk_id = f"{pid}_exchange_aggregated_{i}"
                chunks[chunk_id] = {
                    "process_id": pid,
                    "chunk": chunk,
                    "metadata": {
                        "chunk_type": "exchanges",
                        "product_id": pid,
                        "product_name": m["name"],
                        "uuid": m["uuid"]
                    }
                }

    return chunks

def insert_embeddings(chunks, batch_size=50):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    conn = None
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        chunk_items = list(chunks.items())

        for i in tqdm(range(0, len(chunk_items), batch_size), desc="Inserting Embeddings"):
            batch = chunk_items[i:i + batch_size]
            texts = [item[1]["chunk"] for item in batch]

            try:
                embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=True).tolist()
            except Exception as e:
                logging.error(f"Embedding generation failed for batch {i}-{i+batch_size}: {e}")
                continue

            records = []
            for (chunk_id, data), emb in zip(batch, embeddings):
                records.append((
                    chunk_id,
                    data["process_id"],
                    data["chunk"],
                    emb,
                    Json(data["metadata"])
                ))

            try:
                execute_values(
                    cur,
                    """
                    INSERT INTO embeddings (chunk_id, process_id, chunk, embedding, metadata)
                    VALUES %s
                    ON CONFLICT (chunk_id) DO NOTHING;
                    """,
                    records
                )
            except Exception as e:
                logging.error(f"DB batch insert failed for batch {i}-{i+batch_size}: {e}")

        conn.commit()
        logging.info("All batches inserted successfully.")

    except Exception as e:
        logging.critical(f"Database connection or outer loop failed: {e}")
    finally:
        if conn:
            conn.close()

# Main execution
if __name__ == "__main__":
    chunks = generate_structured_chunks()
    insert_embeddings(chunks)
