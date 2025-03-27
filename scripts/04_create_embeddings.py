import os
import psycopg2
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from collections import defaultdict

# Load environment variables
load_dotenv()

DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

model = SentenceTransformer("all-MiniLM-L6-v2")  # embedding size = 384

def extract_version(process_id, uuid):
    return process_id[len(uuid) + 1:] if process_id and uuid and process_id.startswith(uuid + "_") else None

def connect():
    return psycopg2.connect(**DB_PARAMS)

def fetch_product_metadata():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.process_id, p.name_en, p.description_en, p.reference_year, c.classification
        FROM products p
        LEFT JOIN classifications c ON p.process_id = c.process_id
    """)
    rows = cur.fetchall()
    conn.close()

    metadata = defaultdict(lambda: {
        "name": "", "desc": "", "year": "", "classifications": set()
    })

    for process_id, name, desc, year, classification in rows:
        entry = metadata[process_id]
        entry["name"] = name
        entry["desc"] = desc
        entry["year"] = year
        if classification:
            entry["classifications"].add(classification)

    return metadata

def fetch_exchanges():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.process_id, e.direction, e.flow_en, e.flow_de, e.meanamount, e.unit,
               ema.module, ema.amount
        FROM exchanges e
        LEFT JOIN exchange_moduleamounts ema ON e.exchange_id = ema.exchange_id
    """)
    rows = cur.fetchall()
    conn.close()

    exchanges = defaultdict(list)
    for pid, direction, flow_en, flow_de, amt, unit, module, mod_amt in rows:
        flow = flow_en or flow_de or 'Unnamed Flow'
        if not (flow or amt or mod_amt or module):
            continue
        exchanges[pid].append(
            f"{direction or 'Unknown'}: {flow} | {amt if amt is not None else '–'} {unit or ''} | {module or '–'} = {mod_amt if mod_amt is not None else '–'}"
        )
    return exchanges



def fetch_lcia():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT l.process_id, l.method_en, l.method_de, l.meanamount, l.unit,
               lma.module, lma.amount
        FROM lcia_results l
        LEFT JOIN lcia_moduleamounts lma ON l.lcia_id = lma.lcia_id
    """)
    rows = cur.fetchall()
    conn.close()

    lcia = defaultdict(list)
    for pid, method_en, method_de, amt, unit, module, mod_amt in rows:
        method = method_en or method_de or 'Unnamed Impact'
        if not (method or amt or mod_amt or module):
            continue
        lcia[pid].append(
            f"{method} | {amt if amt is not None else '–'} {unit or ''} | {module or '–'} = {mod_amt if mod_amt is not None else '–'}"
        )
    return lcia



def generate_chunks():
    metadata = fetch_product_metadata()
    exchanges = fetch_exchanges()
    lcia = fetch_lcia()

    chunks = {}

    for pid in metadata:
        uuid = pid.split("_")[0]
        version = extract_version(pid, uuid)

        m = metadata[pid]
        e = exchanges.get(pid, [])
        l = lcia.get(pid, [])

        text = f"""Product: {m["name"]}
                   Year: {m["year"]}
                   Description: {m["desc"]}
                   Classifications: {', '.join(m["classifications"])}
                   Exchanges:\n{chr(10).join(e)}
                   LCIA:\n{chr(10).join(l)}"""

        chunks[pid] = {
            "uuid": uuid,
            "version": version,
            "chunk": text
        }

    return chunks

def insert_embeddings():
    chunks = generate_chunks()
    conn = connect()
    cur = conn.cursor()

    for pid, item in chunks.items():
        embedding = model.encode(item["chunk"]).tolist()
        cur.execute("""
            INSERT INTO epd_embeddings (process_id, uuid, version, embedding, chunk)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (process_id) DO UPDATE
            SET embedding = EXCLUDED.embedding,
                chunk = EXCLUDED.chunk
        """, (pid, item["uuid"], item["version"], embedding, item["chunk"]))

    conn.commit()
    conn.close()
    print(f"✅ Inserted/updated {len(chunks)} embeddings.")

if __name__ == "__main__":
    insert_embeddings()
