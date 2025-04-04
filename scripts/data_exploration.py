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
from PIL import Image

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
    if unit is None:
        return None, None
    unit = str(unit).strip().lower()
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

def fetch_all_classifications():
    query = """
        SELECT process_id, level, classification 
        FROM classifications
        WHERE level IN ('0', '1', '2')
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
        if len(units) == 0:
            continue
        base_unit = units[0]
        common_unit, base_factor = unit_conversion_factor(base_unit)
        if common_unit is None or base_factor is None:
            continue
        for idx, row in group.iterrows():
            unit = row["unit"]
            amount = row[value_col]
            if pd.isna(amount):
                continue
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
    # Fix: Reorder columns according to requirements
    grouped = df.groupby(["indicator_key", "source"])
    stats = grouped.agg(
        name=("name", "first"),
        count=("normalized_amount", "count"),
        original_units=("original_unit", lambda x: ", ".join(sorted(set(x.dropna())))),
        common_unit=("common_unit", "first"),
        mean=("normalized_amount", "mean"),
        std=("normalized_amount", "std"),
        min=("normalized_amount", "min"),
        max=("normalized_amount", "max"),
        median=("normalized_amount", "median")
    ).reset_index()
    
    # Reorder columns as requested
    cols = ["indicator_key", "source", "name", "count", "original_units", "common_unit", 
            "mean", "std", "min", "max", "median"]
    return stats[cols]

def detect_outliers(df, all_classifications):
    """
    Enhanced outlier detection with detailed reasons
    """
    # Final result dataframe with specified columns
    result_columns = ["process_id", "indicator_key", "mean", "unit", "range_min", "range_max", 
                      "amount", "comment"]
    outliers_result = pd.DataFrame(columns=result_columns)
    
    # Get classifications for analysis
    classifications_by_pid = {}
    if not all_classifications.empty:
        for _, row in all_classifications.iterrows():
            pid = row['process_id']
            level = row['level']
            classification = row['classification']
            if pid not in classifications_by_pid:
                classifications_by_pid[pid] = {}
            classifications_by_pid[pid][f'level_{level}'] = classification
    
    # Process each indicator separately
    for indicator_key, indicator_group in df.groupby("indicator_key"):
        if indicator_group["normalized_amount"].isna().all() or len(indicator_group) < 5:
            continue
            
        # Basic statistics for this indicator
        mean_value = indicator_group["normalized_amount"].mean()
        std_value = indicator_group["normalized_amount"].std()
        q1 = indicator_group["normalized_amount"].quantile(0.25)
        q3 = indicator_group["normalized_amount"].quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # Find outliers
        outliers = indicator_group[(indicator_group["normalized_amount"] < lower_bound) | 
                                  (indicator_group["normalized_amount"] > upper_bound)]
        
        if outliers.empty:
            continue
            
        # Classification statistics - calculate means by classification if possible
        class_means = {}
        for level in ['0', '1', '2']:
            level_col = f'level_{level}'
            if any(level_col in pid_data for pid_data in classifications_by_pid.values()):
                # Add classification to data
                temp_df = indicator_group.copy()
                temp_df[level_col] = temp_df['process_id'].apply(
                    lambda pid: classifications_by_pid.get(pid, {}).get(level_col, "Unknown")
                )
                
                # Calculate means by classification
                class_stats = temp_df.groupby(level_col)['normalized_amount'].mean().to_dict()
                class_means[level] = class_stats
        
        # For each outlier, add detailed analysis
        for _, outlier in outliers.iterrows():
            pid = outlier['process_id']
            amount = outlier['normalized_amount']
            unit = outlier['common_unit']
            
            # Generate comment with reason
            comment_parts = []
            
            # Check if extreme outlier (more than 3 IQRs from Q1/Q3)
            extreme_lower = q1 - 3 * iqr
            extreme_upper = q3 + 3 * iqr
            
            if amount < extreme_lower:
                comment_parts.append("Extreme low outlier")
            elif amount < lower_bound:
                comment_parts.append("Low outlier")
            elif amount > extreme_upper:
                comment_parts.append("Extreme high outlier")
            elif amount > upper_bound:
                comment_parts.append("High outlier")
                
            # Check deviation from mean
            std_deviations = abs(amount - mean_value) / std_value if std_value else 0
            if std_deviations > 3:
                comment_parts.append(f"{std_deviations:.1f}σ from mean")
                
            # Check unit inconsistency possibility
            original_unit = outlier['original_unit']
            if "," in indicator_group['original_unit'].str.cat(sep=','):
                comment_parts.append(f"Possible unit inconsistency (using {original_unit})")
                
            # Check classification-based insights
            pid_classifications = classifications_by_pid.get(pid, {})
            for level, class_stats in class_means.items():
                classification = pid_classifications.get(f'level_{level}', "Unknown")
                if classification in class_stats:
                    class_mean = class_stats[classification]
                    if class_mean != 0 and amount != 0:
                        ratio = amount / class_mean
                        if ratio > 5 or ratio < 0.2:
                            comment_parts.append(
                                f"Unusual for {classification} (L{level}) classification "
                                f"(avg: {class_mean:.2e})"
                            )
            
            # If no specific reasons found
            if not comment_parts:
                comment_parts.append("Statistical outlier")
                
            # Create comment
            final_comment = ". ".join(comment_parts)
            
            # Add to results
            new_row = {
                "process_id": pid,
                "indicator_key": indicator_key,
                "mean": mean_value,
                "unit": unit,
                "range_min": lower_bound,
                "range_max": upper_bound,
                "amount": amount,
                "comment": final_comment
            }
            outliers_result = pd.concat([outliers_result, pd.DataFrame([new_row])], ignore_index=True)
    
    return outliers_result

def summarize_by_classification(df, classifications_df):
    """
    Summarize data by classification levels
    """
    if classifications_df.empty:
        return pd.DataFrame(columns=['indicator_key', 'source', 'classification', 'level', 'name', 
                                    'count', 'common_unit', 'mean', 'std', 'min', 'max', 'median'])
    
    results = []
    
    # Process each classification level
    for level in ['0', '1', '2']:
        level_df = classifications_df[classifications_df['level'] == level]
        if level_df.empty:
            continue
# %%            
        # Merge with the data
        merged = df.merge(
            level_df[['process_id', 'classification']], 
            on='process_id', 
            how='inner'  # Only keep rows that have a classification
        )
        
        if merged.empty:
            continue
        
        # Group by classification and calculate statistics
        class_stats = merged.groupby(['indicator_key', 'source', 'classification'])
        class_summary = class_stats.agg(
            name=("name", "first"),
            count=("normalized_amount", "count"),
            common_unit=("common_unit", "first"),
            mean=("normalized_amount", "mean"),
            std=("normalized_amount", "std"),
            min=("normalized_amount", "min"),
            max=("normalized_amount", "max"),
            median=("normalized_amount", "median")
        ).reset_index()
        
        class_summary['level'] = level
        results.append(class_summary)
    
    if not results:
        return pd.DataFrame(columns=['indicator_key', 'source', 'classification', 'level', 'name', 
                                    'count', 'common_unit', 'mean', 'std', 'min', 'max', 'median'])
    
    return pd.concat(results, ignore_index=True)

def create_boxplot(data, indicator, output_path):
    """Create a boxplot using matplotlib"""
    plt.figure(figsize=(10, 6))
    
    # Create a boxplot
    ax = sns.boxplot(x='source', y='normalized_amount', data=data)
    
    # Add title and labels
    plt.title(f"Distribution: {indicator}")
    plt.ylabel("Normalized Amount")
    plt.tight_layout()
    
    # Save figure
    plt.savefig(output_path)
    plt.close()
    
    return output_path

def export_with_data(summary, combined, outliers):
    """
    Export all analysis results to Excel file with proper formatting
    """
    with pd.ExcelWriter("lcia_exchange_analysis.xlsx", engine="openpyxl") as writer:
        # Write summary sheet
        summary.to_excel(writer, sheet_name="Summary", index=False)
        
        # Write outliers sheet with the new format
        outliers.to_excel(writer, sheet_name="Outliers", index=False)
        
        # # Write classification summary
        # classification_summary.to_excel(writer, sheet_name="Classifications", index=False)
        
        # # Write classification stats
        # class_stats.to_excel(writer, sheet_name="ClassificationStats", index=False)
        
        # Get workbook
        workbook = writer.book
        
        # Create individual sheets for each indicator
        for indicator, group in combined.groupby("indicator_key"):
            # Skip if group is empty
            if group.empty:
                continue
                
            # Truncate sheet name to 31 characters (Excel limit)
            sheet_name = indicator[:31]
            
            # Write data
            group.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Create summary section
            sheet = workbook[sheet_name]
            
            # Add indicator summary
            summary_data = summary[summary['indicator_key'] == indicator]
            start_row = len(group) + 3
            
            sheet.cell(row=start_row, column=1).value = "INDICATOR SUMMARY"
            for r_idx, row in enumerate(dataframe_to_rows(summary_data, index=False, header=True), start_row+1):
                for c_idx, value in enumerate(row, 1):
                    sheet.cell(row=r_idx, column=c_idx).value = value
            
            # Add outlier summary
            indicator_outliers = outliers[outliers['indicator_key'] == indicator]
            if not indicator_outliers.empty:
                outlier_start = start_row + 4
                sheet.cell(row=outlier_start, column=1).value = "OUTLIERS"
                for r_idx, row in enumerate(dataframe_to_rows(indicator_outliers, index=False, header=True), outlier_start+1):
                    for c_idx, value in enumerate(row, 1):
                        sheet.cell(row=r_idx, column=c_idx).value = value
            
            # Create box plot using matplotlib instead of plotly
            try:
                if not group['normalized_amount'].isna().all():
                    temp_dir = "temp_plots"
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_path = os.path.join(temp_dir, f"plot_{sheet_name}.png")
                    
                    # Create the plot
                    create_boxplot(group, indicator, temp_path)
                    
                    # Add image to sheet
                    img = XLImage(temp_path)
                    img.anchor = f"L{start_row}"
                    sheet.add_image(img)
            except Exception as e:
                print(f"Warning: Could not create plot for {indicator}: {e}")
    
    # Clean up temporary files
    if os.path.exists("temp_plots"):
        for f in os.listdir("temp_plots"):
            os.remove(os.path.join("temp_plots", f))
        os.rmdir("temp_plots")

def main():
    try:
        print("Fetching LCIA...")
        lcia_df = fetch_lcia_module_amounts()
        print("Fetching Exchanges...")
        exch_df = fetch_exchange_module_amounts()
        print("Fetching all classifications...")
        all_classifications = fetch_all_classifications()
        
        print("Preparing LCIA...")
        lcia_prepped = prepare_lcia(lcia_df)
        print("Preparing Exchanges...")
        exch_prepped = prepare_exchanges(exch_df)
        print("Combining...")
        combined = pd.concat([lcia_prepped, exch_prepped], ignore_index=True)
        print("Summarizing...")
        summary = summarize_combined(combined)
        
        print("Detecting outliers...")
        outliers = detect_outliers(combined, all_classifications)
        
        # print("Summarizing by classification...")
        # class_stats = summarize_by_classification(combined, all_classifications)
        # print("Summarizing classifications...")
        # classification_summary = pd.DataFrame()
        # if not all_classifications.empty:
        #     classification_summary = all_classifications.groupby(
        #         ['level', 'classification']
        #     ).size().reset_index(name='product_count')
        
        print("Exporting results to Excel...")
        export_with_data(summary, combined, outliers)
        print("\n✅ Analysis saved to 'lcia_exchange_analysis.xlsx'")
        
    except Exception as e:
        print(f"Error in main execution: {type(e).__name__}: {e}")
        # Clean up temporary files even if there's an error
        if os.path.exists("temp_plots"):
            for f in os.listdir("temp_plots"):
                os.remove(os.path.join("temp_plots", f))
            os.rmdir("temp_plots")
        raise

if __name__ == "__main__":
    main()
# %%
