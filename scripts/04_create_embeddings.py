import os
import psycopg2
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from collections import defaultdict
import textwrap

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

CHUNK_CHAR_LIMIT = 1500


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
               c.classification
        FROM products p
        LEFT JOIN classifications c ON p.process_id = c.process_id
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
        "classifications": set()
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
            classification
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
        lcia[pid].append(
            f"{method} | {amt if amt is not None else '–'} {unit or ''} | {module or '–'} = {mod_amt if mod_amt is not None else '–'}"
        )
    return lcia

def fetch_compliances():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT process_id, system_en, approval FROM compliances")
    rows = cur.fetchall()
    conn.close()

    compliances = defaultdict(list)
    for pid, system, approval in rows:
        compliances[pid].append(f"{system or 'Unknown system'} - {approval or 'Unknown approval'}")
    return compliances

def fetch_reviews():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT process_id, reviewer, detail_en FROM reviews")
    rows = cur.fetchall()
    conn.close()

    reviews = defaultdict(list)
    for pid, reviewer, detail in rows:
        reviews[pid].append(f"{reviewer or 'Unknown reviewer'}: {detail or 'No detail'}")
    return reviews

def split_text_to_chunks(text, chunk_size):
    return textwrap.wrap(text, chunk_size, break_long_words=False, replace_whitespace=False)

def generate_chunks():
    metadata = fetch_product_metadata()
    exchanges = fetch_exchanges()
    lcia = fetch_lcia()
    compliances = fetch_compliances()
    reviews = fetch_reviews()

    chunks = {}

    for pid in metadata:
        m = metadata[pid]

        shared_header = f"Product: {m['name']} ({m['uuid']})\n"

        sections = [
            ("basic_info", f"Product: {m['name']}\nYear: {m['year']}\nDescription: {m['desc']}\nClassifications: {', '.join(m['classifications'])}"),
            ("technical", f"Geo: {m['geo']} - {m['geo_descr']}\nTechnical Description: {m['tech_descr']}\nTechnical Application: {m['tech_applic']}\nTime Representation: {m['time_repr']}"),
            ("usage", f"Use Advice (EN): {m['use_advice_en']}\nUse Advice (DE): {m['use_advice_de']}"),
            ("meta", f"Generator (EN): {m['generator_en']}\nGenerator (DE): {m['generator_de']}\nEntry By (EN): {m['entry_by_en']}\nEntry By (DE): {m['entry_by_de']}\nAdmin Version: {m['admin_version']}\nLicense Type: {m['license_type']}\nAccess (EN): {m['access_en']}\nAccess (DE): {m['access_de']}\nTimestamp: {m['timestamp']}\nFormats: {m['formats']}"),
            ("compliances", "\n".join(compliances.get(pid, []))),
            ("reviews", "\n".join(reviews.get(pid, []))),
            ("exchanges", "\n".join(exchanges.get(pid, []))),
            ("lcia", "\n".join(lcia.get(pid, []))),
        ]

        for section, text in sections:
            sub_chunks = split_text_to_chunks(text, CHUNK_CHAR_LIMIT - len(shared_header))
            for i, chunk in enumerate(sub_chunks):
                chunk_id = f"{pid}_{section}_{i}"
                chunks[chunk_id] = {
                    "process_id": pid,
                    "chunk": shared_header + chunk
                }

    return chunks

def insert_embeddings():
    chunks = generate_chunks()
    conn = connect()
    cur = conn.cursor()

    for chunk_id, item in chunks.items():
        embedding = model.encode(item["chunk"]).tolist()
        cur.execute("""
            INSERT INTO epd_embeddings (chunk_id, process_id, embedding, chunk)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO UPDATE
            SET embedding = EXCLUDED.embedding,
                chunk = EXCLUDED.chunk
        """, (chunk_id, item["process_id"], embedding, item["chunk"]))

    conn.commit()
    conn.close()
    print(f"✅ Inserted/updated {len(chunks)} chunks.")

if __name__ == "__main__":
    insert_embeddings()
