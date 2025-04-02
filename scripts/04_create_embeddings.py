from sentence_transformers import SentenceTransformer
from collections import defaultdict
import psycopg2
import textwrap
import os
from dotenv import load_dotenv
from psycopg2.extras import Json

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
EMBEDDING_DIM = 1024  # For bge-large-en-v1.5
model = SentenceTransformer("BAAI/bge-large-en-v1.5")

def fetch_metadata():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("SELECT process_id, name, uuid FROM epd_metadata")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {pid: {"name": name, "uuid": uuid} for pid, name, uuid in rows}

def fetch_lcia():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("""
        SELECT process_id, method_en, method_de, indicator_key, mean_amount, unit, stage, scenario, amount
        FROM epd_lcia
    """)
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

def fetch_exchanges():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("""
        SELECT process_id, flow_name, unit, stage, scenario, value
        FROM epd_exchanges
    """)
    exchanges = defaultdict(list)
    for row in cur.fetchall():
        pid, flow, unit, stage, scenario, value = row
        exchanges[pid].append({
            "flow_en": flow,
            "unit": unit,
            "module": stage,
            "scenario": scenario,
            "amount": value
        })
    cur.close()
    conn.close()
    return exchanges

def generate_structured_chunks(metadata, lcia, exchanges):
    chunks = {}

    for pid in metadata:
        m = metadata[pid]

        # LCIA by stage
        stage_data = defaultdict(list)
        for entry in lcia.get(pid, []):
            stage = entry["module"]
            scenario = entry["scenario"]
            line = f"{entry['method_en']} ({entry['indicator_key']}) = {entry['amount']} {entry['unit']}"
            if scenario:
                line += f" (Scenario: {scenario})"
            stage_data[(stage, scenario)].append(line)

        for (stage, scenario), entries in stage_data.items():
            text = f"Product: {m['name']} ({m['uuid']})\nStage: {stage}"
            if scenario:
                text += f" (Scenario: {scenario})"
            text += "\n" + "\n".join(entries)
            for i, chunk in enumerate(textwrap.wrap(text.strip(), CHUNK_CHAR_LIMIT)):
                chunk_id = f"{pid}_lcia_{stage}_{i}"
                chunks[chunk_id] = {
                    "process_id": pid,
                    "chunk": chunk,
                    "metadata": {
                        "chunk_type": "lcia_by_stage",
                        "product_id": pid,
                        "product_name": m["name"],
                        "uuid": m["uuid"],
                        "stage": stage,
                        "scenario": scenario
                    }
                }

        # LCIA aggregated
        indicator_data = defaultdict(dict)
        for entry in lcia.get(pid, []):
            indicator = entry["indicator_key"]
            unit = entry["unit"]
            stage = entry["module"]
            scenario = entry["scenario"]
            label = f"{stage}" + (f":{scenario}" if scenario else "")
            indicator_data[indicator][label] = f"{entry['amount']} {unit}"

        for indicator, stages in indicator_data.items():
            lines = [f"{label}: {val}" for label, val in stages.items()]
            text = f"Product: {m['name']} ({m['uuid']})\nIndicator: {indicator}\n" + "\n".join(lines)
            for i, chunk in enumerate(textwrap.wrap(text.strip(), CHUNK_CHAR_LIMIT)):
                chunk_id = f"{pid}_indicator_{indicator.replace(' ', '_')}_{i}"
                chunks[chunk_id] = {
                    "process_id": pid,
                    "chunk": chunk,
                    "metadata": {
                        "chunk_type": "indicator_across_stages",
                        "product_id": pid,
                        "product_name": m["name"],
                        "uuid": m["uuid"],
                        "indicator": indicator
                    }
                }

        # Exchanges by stage
        exchange_stage_data = defaultdict(list)
        for entry in exchanges.get(pid, []):
            stage = entry["module"]
            scenario = entry["scenario"]
            line = f"{entry['flow_en']} = {entry['amount']} {entry['unit']}"
            if scenario:
                line += f" (Scenario: {scenario})"
            exchange_stage_data[(stage, scenario)].append(line)

        for (stage, scenario), entries in exchange_stage_data.items():
            text = f"Product: {m['name']} ({m['uuid']})\nStage: {stage}"
            if scenario:
                text += f" (Scenario: {scenario})"
            text += "\n" + "\n".join(entries)
            for i, chunk in enumerate(textwrap.wrap(text.strip(), CHUNK_CHAR_LIMIT)):
                chunk_id = f"{pid}_exchange_{stage}_{i}"
                chunks[chunk_id] = {
                    "process_id": pid,
                    "chunk": chunk,
                    "metadata": {
                        "chunk_type": "exchange_by_stage",
                        "product_id": pid,
                        "product_name": m["name"],
                        "uuid": m["uuid"],
                        "stage": stage,
                        "scenario": scenario
                    }
                }

        # Exchanges aggregated
        exchange_data = defaultdict(dict)
        for entry in exchanges.get(pid, []):
            flow = entry["flow_en"]
            stage = entry["module"]
            scenario = entry["scenario"]
            label = f"{stage}" + (f":{scenario}" if scenario else "")
            exchange_data[flow][label] = f"{entry['amount']} {entry['unit']}"

        for flow, stages in exchange_data.items():
            lines = [f"{label}: {val}" for label, val in stages.items()]
            text = f"Product: {m['name']} ({m['uuid']})\nExchange Flow: {flow}\n" + "\n".join(lines)
            for i, chunk in enumerate(textwrap.wrap(text.strip(), CHUNK_CHAR_LIMIT)):
                chunk_id = f"{pid}_exchange_indicator_{flow.replace(' ', '_')}_{i}"
                chunks[chunk_id] = {
                    "process_id": pid,
                    "chunk": chunk,
                    "metadata": {
                        "chunk_type": "exchange_across_stages",
                        "product_id": pid,
                        "product_name": m["name"],
                        "uuid": m["uuid"],
                        "indicator": flow
                    }
                }

    return chunks

def insert_embeddings(chunks):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    for chunk_id, data in chunks.items():
        embedding = model.encode(data["chunk"]).tolist()
        cur.execute("""
            INSERT INTO epd_embeddings (chunk_id, process_id, chunk, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO NOTHING;
        """, (
            chunk_id,
            data["process_id"],
            data["chunk"],
            embedding,
            Json(data["metadata"])
        ))

    conn.commit()
    cur.close()
    conn.close()

# Main execution
if __name__ == "__main__":
    metadata = fetch_metadata()
    lcia = fetch_lcia()
    exchanges = fetch_exchanges()
    chunks = generate_structured_chunks(metadata, lcia, exchanges)
    insert_embeddings(chunks)
