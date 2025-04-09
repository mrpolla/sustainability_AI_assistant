import os
import json
import psycopg2

# === Load DB credentials from environment ===
DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

# === JSON file path ===
JSON_FILE = os.path.join("data", "materials_and_uses", "materials_and_uses.json")

# === Load LLM Output JSON ===
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# === Prepare Data ===
materials_data = []
uses_data = []

for item in data:
    process_id = item.get("process_id")
    materials = item.get("llm_analysis", {}).get("materials", [])
    uses = item.get("llm_analysis", {}).get("uses", [])

    for i, material in enumerate(materials):
        materials_data.append((process_id, material.strip(), i + 1))

    for i, use in enumerate(uses):
        uses_data.append((process_id, use.strip(), i + 1))

# === Insert into Database ===
try:
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    # Insert materials
    cur.executemany(
        """
        INSERT INTO materials (process_id, material, list_order)
        VALUES (%s, %s, %s)
        """,
        materials_data
    )

    # Insert uses
    cur.executemany(
        """
        INSERT INTO uses (process_id, use_case, list_order)
        VALUES (%s, %s, %s)
        """,
        uses_data
    )

    conn.commit()
    print("✅ Data inserted successfully.")

except Exception as e:
    print("❌ Error inserting data:", e)

finally:
    if conn:
        cur.close()
        conn.close()
