import os
import json
import re
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

MAX_SENTENCES_PER_CHUNK = 4

# ---------- Sentence Utilities ----------

def split_into_sentences(text):
    if not text or text.strip() == '':
        return []

    text = re.sub(r'^\d+(\.\d+)*\s*', '', text)
    text = text.replace('.\n', '.[SENTENCEBREAK]')
    text = re.sub(r'\nNote \d+ to entry:', '[SENTENCEBREAK]Note to entry:', text)
    text = re.sub(r'\n\n+', '[SENTENCEBREAK]', text)
    text = text.replace('\n', ' ')

    sentences = re.split(r'\.(?=\s|$)|\?(?=\s|$)|\!(?=\s|$)|(?:\[SENTENCEBREAK\])', text)
    return [s.strip() for s in sentences if s.strip()]

def create_chunks(sentences, max_sentences=MAX_SENTENCES_PER_CHUNK):
    chunks = []
    for i in range(0, len(sentences), max_sentences):
        part = sentences[i:i + max_sentences]
        joined = '. '.join(part)
        chunk = joined if joined.endswith('.') else joined + '.'
        chunks.append(chunk)
    return chunks

# ---------- Database Fetching ----------

def connect():
    return psycopg2.connect(**DB_PARAMS)

def fetch_all_epd_fields():
    conn = connect()
    cur = conn.cursor()

    # Fetch core product info
    cur.execute("""
        SELECT 
            p.process_id, p.uuid,
            COALESCE(p.name_en, p.name_en_ai) AS name,
            COALESCE(p.description_en, p.description_en_ai) AS description,
            COALESCE(p.tech_descr_en, p.tech_descr_en_ai) AS tech_descr,
            COALESCE(p.tech_applic_en, p.tech_applic_en_ai) AS tech_applic,
            p.short_desc_en_ai, p.reference_year, p.valid_until,
            p.category_level_1, p.category_level_2, p.category_level_3,
            p.name_en, p.name_en_ai, p.description_en, p.description_en_ai,
            p.tech_descr_en, p.tech_descr_en_ai, p.tech_applic_en, p.tech_applic_en_ai
        FROM products p
        LIMIT 100
    """)
    products = cur.fetchall()

    product_data = {}

    for row in products:
        (pid, uuid, name, desc, tech_descr, tech_applic,
         short_desc, year, until,
         cat1, cat2, cat3,
         name_en, name_en_ai, desc_en, desc_en_ai,
         tech_en, tech_ai, applic_en, applic_ai) = row

        product_data[pid] = {
            "uuid": uuid,
            "product_name": name,
            "category_level_1": cat1,
            "category_level_2": cat2,
            "category_level_3": cat3,
            "materials": [],
            "use_cases": [],
            "fields": {}
        }

        # Track fallback sources explicitly
        if name_en:
            product_data[pid]["fields"]["name_en"] = name_en
        elif name_en_ai:
            product_data[pid]["fields"]["name_en_ai"] = name_en_ai

        if desc_en:
            product_data[pid]["fields"]["description_en"] = desc_en
        elif desc_en_ai:
            product_data[pid]["fields"]["description_en_ai"] = desc_en_ai

        if tech_en:
            product_data[pid]["fields"]["tech_descr_en"] = tech_en
        elif tech_ai:
            product_data[pid]["fields"]["tech_descr_en_ai"] = tech_ai

        if applic_en:
            product_data[pid]["fields"]["tech_applic_en"] = applic_en
        elif applic_ai:
            product_data[pid]["fields"]["tech_applic_en_ai"] = applic_ai

        if short_desc:
            product_data[pid]["fields"]["short_desc_en_ai"] = short_desc
        if year:
            product_data[pid]["fields"]["reference_year"] = str(year)
        if until:
            product_data[pid]["fields"]["valid_until"] = str(until)

    # Fetch and group materials
    cur.execute("SELECT process_id, material FROM materials")
    for pid, material in cur.fetchall():
        if pid in product_data and material:
            product_data[pid]["materials"].append(material)

    # Fetch and group uses
    cur.execute("SELECT process_id, use_case FROM uses")
    for pid, use_case in cur.fetchall():
        if pid in product_data and use_case:
            product_data[pid]["use_cases"].append(use_case)

    cur.close()
    conn.close()
    return product_data

# ---------- Chunking & Saving ----------

def generate_chunks():
    all_data = fetch_all_epd_fields()
    output_chunks = []

    for pid, data in all_data.items():
        uuid = data["uuid"]
        product_name = data["product_name"]
        cat1 = data.get("category_level_1", "")
        cat2 = data.get("category_level_2", "")
        cat3 = data.get("category_level_3", "")
        materials = data.get("materials", [])
        uses = data.get("use_cases", [])
        fields = data["fields"]

        # Handle regular fields
        for section_name, text in fields.items():
            if not text or not isinstance(text, str) or not text.strip():
                continue

            sentences = split_into_sentences(text)
            chunks = create_chunks(sentences)

            for i, chunk in enumerate(chunks):
                chunk_id = f"{pid}_{section_name}_{i}"
                output_chunks.append({
                    "chunk_id": chunk_id,
                    "chunk": chunk,
                    "metadata": {
                        "source": "epd",
                        "section": section_name,
                        "product_id": pid,
                        "uuid": uuid,
                        "product_name": product_name,
                        "category_level_1": cat1,
                        "category_level_2": cat2,
                        "category_level_3": cat3,
                        "materials": materials,
                        "use_cases": uses
                    }
                })

    return output_chunks

def save_to_json(chunks, filename="epd_chunks.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(chunks)} chunks to {filename}")

if __name__ == "__main__":
    chunks = generate_chunks()
    save_to_json(chunks)
