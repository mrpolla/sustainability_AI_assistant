import os
import psycopg2
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import re
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils.dataframe import dataframe_to_rows

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

def unit_conversion_factor(unit):
    unit = unit.strip().lower()
    replacements = {
        "äq": "eq", "äquiv": "eq", "äqv": "eq", "äqu": "eq", "eqv": "eq", "äquiv.": "eq", "äq.": "eq", "ä": "a",
        " ": "", "v.": "v", "eq.": "eq", "eqv.": "eq", "equiv.": "eq", "_": "", "−": "-", "–": "-"
    }
    for old, new in replacements.items():
        unit = unit.replace(old, new)
    unit = unit.replace("³", "^3").replace("²", "^2")
    patterns = {
        r"^kg.*": ("kg", 1), r"^g.*": ("kg", 1e-3), r"^mg.*": ("kg", 1e-6), r"^t.*": ("kg", 1e3),
        r"^mol.*": ("mol", 1), r"^mole.*": ("mol", 1),
        r"^mj.*": ("MJ", 1), r"^kwh.*": ("MJ", 3.6),
        r"^m3.*": ("m3", 1), r"^m\^3.*": ("m3", 1), r"^l.*": ("m3", 1e-3), r"^cm3.*": ("m3", 1e-6),
        r"^m2.*": ("m2", 1), r"^m\^2.*": ("m2", 1),
        r"^kbq.*": ("kBq", 1), r"^ctue.*": ("CTUe", 1), r"^ctuh.*": ("CTUh", 1), r"^sqp.*": ("SQP", 1),
        r"^diseaseincidence.*": ("disease_incidence", 1), r"^krankheitsfälle.*": ("disease_incidence", 1),
        r"^-+$": (None, None), r"^dimensionless.*": ("dimensionless", 1)
    }
    for pattern, (common, factor) in patterns.items():
        if re.match(pattern, unit):
            return common, factor
    print(f"⚠️ Unrecognized unit: '{unit}'")
    return None, None

def fetch_lcia_module_amounts():
    query = """
        SELECT lr.method_en, lr.indicator_key, lr.unit, lma.module, lma.amount,
               lr.process_id, c.classification
        FROM lcia_results lr
        JOIN lcia_moduleamounts lma ON lr.lcia_id = lma.lcia_id
        LEFT JOIN classifications c ON lr.process_id = c.process_id AND c.level = '2'
        WHERE lma.amount IS NOT NULL
    """
    with connect() as conn:
        return pd.read_sql(query, conn)

def fetch_exchange_module_amounts():
    query = """
        SELECT e.flow_en, e.indicator_key, e.direction, e.unit, ema.module, ema.amount,
               e.process_id, c.classification
        FROM exchanges e
        JOIN exchange_moduleamounts ema ON e.exchange_id = ema.exchange_id
        LEFT JOIN classifications c ON e.process_id = c.process_id AND c.level = '2'
        WHERE ema.amount IS NOT NULL
    """
    with connect() as conn:
        return pd.read_sql(query, conn)

def normalize_units_with_metadata(df, group_cols, value_col="amount"):
    df = df.copy()
    df["original_unit"] = df["unit"]
    df["common_unit"] = None
    df["normalized_amount"] = np.nan
    for keys, group in df.groupby(group_cols):
        units = group["unit"].dropna().unique()
        base_unit = units[0]
        common_unit, base_factor = unit_conversion_factor(base_unit)
        if common_unit is None or base_factor is None:
            continue
        for idx, row in group.iterrows():
            unit = row["unit"]
            amount = row[value_col]
            _, factor = unit_conversion_factor(unit)
            if factor is not None:
                norm_value = amount * (factor / base_factor)
                df.at[idx, "normalized_amount"] = norm_value
                df.at[idx, "common_unit"] = common_unit
    return df

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
        median=("normalized_amount", "median")
    ).reset_index()
    return stats

def detect_outliers(df):
    outliers = []
    for indicator, group in df.groupby("indicator_key"):
        q1 = group["normalized_amount"].quantile(0.25)
        q3 = group["normalized_amount"].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        group_outliers = group[(group["normalized_amount"] < lower) | (group["normalized_amount"] > upper)]
        if not group_outliers.empty:
            outliers.append((indicator, group_outliers))
    return outliers


def export_with_data(summary, combined, outliers):
    with pd.ExcelWriter("lcia_exchange_analysis.xlsx", engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        for indicator, group in combined.groupby("indicator_key"):
            sheet = indicator[:31]
            group.to_excel(writer, sheet_name=sheet, index=False)

        out_df = pd.concat([g.assign(indicator_key=k) for k, g in outliers], ignore_index=True)
        out_df.to_excel(writer, sheet_name="Outliers", index=False)

# def export_with_plots(summary, combined, outliers):
#     with pd.ExcelWriter("lcia_exchange_analysis.xlsx", engine="openpyxl") as writer:
#         summary.to_excel(writer, sheet_name="Summary", index=False)
#         for indicator, group in combined.groupby("indicator_key"):
#             sheet = indicator[:31]
#             group.to_excel(writer, sheet_name=sheet, index=False)
#             fig, axes = plt.subplots(1, 2, figsize=(12, 4))
#             if group['source'].nunique() > 1:
#                 sns.boxplot(data=group, x="source", y="normalized_amount", ax=axes[0])
#             else:
#                 single_label = group['source'].iloc[0]
#                 sns.boxplot(x=[single_label] * len(group), y=group['normalized_amount'], ax=axes[0])
#                 axes[0].set_xlabel("source")
#                 axes[0].set_xlabel("source")
#                 axes[0].set_xticks([0])
#                 axes[0].set_xticklabels([group["source"].iloc[0]])
#             sns.histplot(data=group, x="normalized_amount", hue="source", kde=False, bins=50, ax=axes[1])
#             plt.tight_layout()
#             img_stream = BytesIO()
#             plt.savefig(img_stream, format='png')
#             plt.close()
#             img_stream.seek(0)
#             book = writer.book
#             sheet_obj = book[sheet]
#             img = XLImage(img_stream)
#             img.anchor = "J2"
#             sheet_obj.add_image(img)

#         out_df = pd.concat([g.assign(indicator_key=k) for k, g in outliers], ignore_index=True)
#         out_df.to_excel(writer, sheet_name="Outliers", index=False)

def main():
    print("Fetching LCIA...")
    lcia_df = fetch_lcia_module_amounts()
    print("Fetching Exchanges...")
    exch_df = fetch_exchange_module_amounts()
    print("Preparing LCIA...")
    lcia_prepped = prepare_lcia(lcia_df)
    print("Preparing Exchanges...")
    exch_prepped = prepare_exchanges(exch_df)
    print("Combining...")
    combined = pd.concat([lcia_prepped, exch_prepped], ignore_index=True)
    print("Summarizing...")
    summary = summarize_combined(combined)
    print("Detecting outliers...")
    outliers = detect_outliers(combined)
    print("Exporting results with plots to Excel...")
    export_with_data(summary, combined, outliers)
    print("\n✅ Analysis saved to 'lcia_exchange_analysis.xlsx'")

if __name__ == "__main__":
    main()
