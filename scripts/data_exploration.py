import os
import psycopg2
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# === Load DB Credentials from .env ===
load_dotenv()
DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

def connect():
    return psycopg2.connect(**DB_PARAMS)

# === Unit conversion ===
def unit_conversion_factor(unit):
    """Returns common unit and conversion factor from given unit to common unit"""
    conversion = {
        "mg": ("kg", 1e-6),
        "g": ("kg", 1e-3),
        "kg": ("kg", 1),
        "t": ("kg", 1e3),

        "MJ": ("MJ", 1),
        "kWh": ("MJ", 3.6),  # 1 kWh = 3.6 MJ

        "l": ("m3", 1e-3),
        "cm3": ("m3", 1e-6),
        "m3": ("m3", 1),

        "cm2": ("m2", 1e-4),
        "mm2": ("m2", 1e-6),
        "m2": ("m2", 1),
    }
    return conversion.get(unit, (None, None))

# === Data Fetching ===
def fetch_lcia_module_amounts():
    query = """
        SELECT lr.method_en, lr.indicator_key, lr.unit, lma.module, lma.amount
        FROM lcia_results lr
        JOIN lcia_moduleamounts lma ON lr.lcia_id = lma.lcia_id
        WHERE lma.amount IS NOT NULL
    """
    with connect() as conn:
        return pd.read_sql(query, conn)

def fetch_exchange_module_amounts():
    query = """
        SELECT e.flow_en, e.indicator_key, e.direction, e.unit, ema.module, ema.amount
        FROM exchanges e
        JOIN exchange_moduleamounts ema ON e.exchange_id = ema.exchange_id
        WHERE ema.amount IS NOT NULL
    """
    with connect() as conn:
        return pd.read_sql(query, conn)

# === Unit Normalization ===
def normalize_units_with_metadata(df, group_cols, value_col="amount"):
    df = df.copy()
    df["original_unit"] = df["unit"]
    df["common_unit"] = None
    df["normalized_amount"] = np.nan

    for keys, group in df.groupby(group_cols):
        units = group["unit"].dropna().unique()
        base_unit = units[0]  # Choose first seen
        common_unit, base_factor = unit_conversion_factor(base_unit)

        if common_unit is None or base_factor is None:
            continue  # Skip unknown

        for idx, row in group.iterrows():
            unit = row["unit"]
            amount = row[value_col]
            _, factor = unit_conversion_factor(unit)

            if factor is not None:
                norm_value = amount * (factor / base_factor)
                df.at[idx, "normalized_amount"] = norm_value
                df.at[idx, "common_unit"] = common_unit

    return df

# === Data Preparation ===
def prepare_lcia(df):
    df = df.copy()
    df["name"] = df["method_en"]
    df["source"] = "LCIA"
    return normalize_units_with_metadata(df, ["indicator_key"])

def prepare_exchanges(df):
    df = df.copy()
    df["name"] = df["flow_en"]
    df["source"] = "Exchange"
    return normalize_units_with_metadata(df, ["indicator_key"])

# === Summarization ===
def summarize_combined(df):
    grouped = df.groupby(["indicator_key", "common_unit", "source"])
    stats = grouped.agg(
        name=("name", "first"),
        original_units=("original_unit", lambda x: ", ".join(sorted(set(x.dropna())))),
        count=("normalized_amount", "count"),
        mean=("normalized_amount", "mean"),
        std=("normalized_amount", "std"),
        min=("normalized_amount", "min"),
        max=("normalized_amount", "max"),
        median=("normalized_amount", "median"),
    ).reset_index()
    return stats

# === Main ===
def main():
    print("Fetching LCIA...")
    lcia_df = fetch_lcia_module_amounts()
    print(f"LCIA rows: {len(lcia_df)}")

    print("Fetching Exchanges...")
    exch_df = fetch_exchange_module_amounts()
    print(f"Exchange rows: {len(exch_df)}")

    print("Preparing LCIA...")
    lcia_prepped = prepare_lcia(lcia_df)

    print("Preparing Exchanges...")
    exch_prepped = prepare_exchanges(exch_df)

    print("Combining and summarizing...")
    combined = pd.concat([lcia_prepped, exch_prepped], ignore_index=True)
    summary = summarize_combined(combined)

    print(summary)
    summary.to_excel("combined_lcia_exchange_summary.xlsx", index=False)
    print("\nSaved to 'combined_lcia_exchange_summary.xlsx'")

if __name__ == "__main__":
    main()
