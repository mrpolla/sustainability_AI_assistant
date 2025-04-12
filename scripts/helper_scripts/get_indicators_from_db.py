import psycopg2
import pandas as pd
from collections import Counter

# Connect to your database
conn = psycopg2.connect(
    dbname="your_db",
    user="your_user",
    password="your_password",
    host="your_host",
    port="your_port"
)
cur = conn.cursor()

# Fetch indicator_key + method_en from lcia_results
cur.execute("""
    SELECT indicator_key, method_en
    FROM lcia_results
    WHERE indicator_key IS NOT NULL
""")
lcia_rows = cur.fetchall()
lcia_indicators = pd.DataFrame(lcia_rows, columns=["indicator_key", "method_en"])

# Fetch indicator_key + flow_en from exchanges
cur.execute("""
    SELECT indicator_key, flow_en
    FROM exchanges
    WHERE indicator_key IS NOT NULL
""")
exchange_rows = cur.fetchall()
exchange_indicators = pd.DataFrame(exchange_rows, columns=["indicator_key", "flow_en"])

# Count the most common method_en for each indicator in LCIA
lcia_common = lcia_indicators.groupby('indicator_key')['method_en'].agg(lambda x: Counter(x).most_common(1)[0][0])
exchange_common = exchange_indicators.groupby('indicator_key')['flow_en'].agg(lambda x: Counter(x).most_common(1)[0][0])

# Merge all indicators
all_keys = set(lcia_indicators['indicator_key']).union(set(exchange_indicators['indicator_key']))
missing_keys = {
    "lcia": ["GWP", "EP", "IRP"],
    "exchanges": ["SF"]
}

print("Missing LCIA indicators:", [k for k in missing_keys['lcia'] if k not in lcia_indicators['indicator_key'].unique()])
print("Missing exchange indicators:", [k for k in missing_keys['exchanges'] if k not in exchange_indicators['indicator_key'].unique()])

# Create indicators table
cur.execute("""
    DROP TABLE IF EXISTS indicators;
    CREATE TABLE indicators (
        indicator_key TEXT PRIMARY KEY,
        name_en TEXT,
        description_en TEXT
    )
""")

# Combine and insert into indicators table
for indicator in sorted(all_keys):
    method = lcia_common.get(indicator, "")
    flow = exchange_common.get(indicator, "")
    description = f"Most common method: {method}; Most common flow: {flow}"
    cur.execute("""
        INSERT INTO indicators (indicator_key, name_en, description_en)
        VALUES (%s, %s, %s)
    """, (indicator, indicator, description))

conn.commit()
cur.close()
conn.close()
print("Indicators table created successfully.")
