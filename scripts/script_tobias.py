import psycopg2
import pandas as pd
from urllib.parse import urlparse, parse_qs
from collections import defaultdict
import os

# === DB Connection ===
def connect():
    return psycopg2.connect(
        dbname="EDP_AI_assistant",
        user="postgres",
        password="admin",
        host="localhost",
        port="5432"
    )

# === UUID Extraction ===
def extract_uuid(link):
    parsed = urlparse(str(link))
    query = parse_qs(parsed.query)
    return query.get("uuid", [""])[0]

# === Fetch All Indicators ===
def fetch_indicators(uuids):
    conn = connect()
    cur = conn.cursor()

    # LCIA results
    cur.execute(f"""
        SELECT p.uuid, l.method_en, l.method_de, l.indicator_key, l.unit,
               lma.module, lma.amount, lma.scenario
        FROM products p
        JOIN lcia_results l ON p.process_id = l.process_id
        LEFT JOIN lcia_moduleamounts lma ON l.lcia_id = lma.lcia_id
        WHERE p.uuid = ANY(%s)
    """, (uuids,))
    lcia_rows = cur.fetchall()

    # Exchanges
    cur.execute(f"""
        SELECT p.uuid, e.flow_en, e.flow_de, e.indicator_key, e.unit,
               ema.module, ema.amount, ema.scenario
        FROM products p
        JOIN exchanges e ON p.process_id = e.process_id
        LEFT JOIN exchange_moduleamounts ema ON e.exchange_id = ema.exchange_id
        WHERE p.uuid = ANY(%s)
    """, (uuids,))
    exchange_rows = cur.fetchall()
    conn.close()

    indicators = defaultdict(lambda: defaultdict(lambda: {"unit": "", "modules": defaultdict(float)}))

    for uuid, method_en, method_de, indicator_key, unit, module, amount, scenario in lcia_rows:
        method = method_en or method_de or indicator_key
        indicators[uuid][method]["unit"] = unit
        if module and amount is not None:
            key = module if module not in ["C1", "C2", "C3", "C4", "D"] else f"{module}_{scenario}"
            indicators[uuid][method]["modules"][key] += amount

    for uuid, flow_en, flow_de, indicator_key, unit, module, amount, scenario in exchange_rows:
        flow = flow_en or flow_de or indicator_key
        indicators[uuid][flow]["unit"] = unit
        if module and amount is not None:
            key = module if module not in ["C1", "C2", "C3", "C4", "D"] else f"{module}_{scenario}"
            indicators[uuid][flow]["modules"][key] += amount

    return indicators

# === Mapping of Descriptions to Modules ===
MODULE_MAPPING = [
    ("Rohstoffbereitstellung", "A1"),
    ("Herstellung", "A1-A3"),
    ("Transport", "A2"),
    ("Herstellung", "A3"),
    ("Transport", "A4"),
    ("Einbau", "A5"),
    ("Nutzung", "B1"),
    ("Instandhaltung", "B2"),
    ("Reparatur", "B3"),
    ("Ersatz", "B4"),
    ("Umbau/Erneuerung", "B5"),
    ("Energieeinsatz", "B6"),
    ("Wassereinsatz", "B7"),
    ("Abbruch", "C1"),
    ("Abbruch", "C1"),
    ("Transport", "C2"),
    ("Transport", "C2"),
    ("Abfallbehandlung", "C3"),
    ("Abfallbehandlung", "C3"),
    ("Beseitigung", "C4"),
    ("Beseitigung", "C4"),
    ("Recyclingpotential", "D"),
    ("Recyclingpotential", "D")
]

# === Main Logic ===
def main():
    # Load Excel
    df = pd.read_excel(
        os.path.join(os.getcwd(), "Ökobaudat Tobias 2025-03-13.xlsx"),
        usecols="A:D",
        skiprows=2  # Skip the first three rows
    )
    df.columns = ["MAT-ID", "Material/Werkstoff", "Datenbank", "Link"]
    df["UUID"] = df["Link"].apply(extract_uuid)
    uuids = df["UUID"].dropna().tolist()

    # Fetch all indicators
    indicator_data = fetch_indicators(uuids)

    # Header rows
    descriptions = ["MAT-ID", "Material/Werkstoff", "Datenbank", "Link", "UUID", "Indikator", "Einheit"] + [desc for desc, mod in MODULE_MAPPING]
    modules = ["", "", "", "", "", "", ""] + [mod for desc, mod in MODULE_MAPPING]
    scenarios = ["", "", "", "", "", "", ""] + [""] * len(MODULE_MAPPING)

    data_rows = []

    for _, row in df.iterrows():
        uuid = row["UUID"]
        indicators = indicator_data.get(uuid, {})
        gwp_key = next((key for key in indicators if "GWP-total" in key), None)
        gwp = indicators.get(gwp_key, {})
        unit = gwp.get("unit", "")
        module_vals = gwp.get("modules", {})

        # Include original columns A, B, C, and Link in the row data
        row_data = [str(row["MAT-ID"]), str(row["Material/Werkstoff"]), str(row["Datenbank"]), str(row["Link"]), uuid, gwp_key, unit]
        row_scenarios = []

        # Fill module values based on MODULE_MAPPING
        for _, mod in MODULE_MAPPING:
            # Match keys in module_vals that start with the module prefix
            matched = [(k, v) for k, v in module_vals.items() if k.startswith(mod)]
            if matched:
                k, v = matched[0]
                scenario = k.split("_")[1] if "_" in k else ""
                row_data.append(v)
                row_scenarios.append(scenario)
            else:
                row_data.append(0)
                row_scenarios.append("")

        data_rows.append(row_data)

        # Update scenarios row
        for i, scenario in enumerate(row_scenarios):
            if not scenarios[i + 6]:  # Don't overwrite
                scenarios[i + 6] = scenario

    # Save to CSV
    final_df = pd.DataFrame([descriptions, modules, scenarios] + data_rows)
    final_df.to_csv("gwp_total_cleaned.csv", index=False, header=False)
    print("✅ Exported to gwp_total_cleaned.csv")

if __name__ == "__main__":
    main()
