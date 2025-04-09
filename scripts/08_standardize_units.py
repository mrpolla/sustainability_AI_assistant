import psycopg2
import pandas as pd
import os
import re
from dotenv import load_dotenv

# Load environment variables from .env file (for database credentials)
load_dotenv()

not_found_units = []
def normalize_unit(unit):
    """
    Standardize unit names to a consistent format.
    Comprehensive version that handles all units found in the CSV files.
    """
    import re
    
    if not isinstance(unit, str):
        return unit
    
    # Handle NULL values
    if unit.upper() == "NULL" or unit.strip() == "":
        return "-"
    
    unit = unit.strip().lower()
    
    # Standard mappings with expanded patterns
    mappings = {
        # Volume units
        r"^m[\^³]?[3]?$": "m3",
        r"^m\s*[3³]$": "m3",
        r"^m\^3$": "m3",
        r"^m³.*$": "m3",
        
        # Carbon dioxide equivalents with various notations
        r"^kg.*co.*?2.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg CO2 eq",
        r"^kg.*co.*?\(?2\)?.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg CO2 eq",
        r"^kg.*co_?\(?2\)?[- ]?äq\.?$": "kg CO2 eq",
        r"^kg\s*co_?\(?2\)?(?:\s|-|_).*$": "kg CO2 eq",
        
        # CFC equivalents
        r"^kg.*(?:cfc|r)\s*11.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg CFC-11 eq",
        r"^kg.*(?:cfc|r)11.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg CFC-11 eq",
        r"^kg\s*cfc-11\s*eq\.?$": "kg CFC-11 eq",
        
        # Phosphorus equivalents
        r"^kg.*p(?:[ -]?eq|\s?äq|\s?aeq|\s?äqv|\s?eqv|[- ]?äquiv|\s?equivalent).*$": "kg P eq",
        r"^kg.*p[- ]?äq.*$": "kg P eq",
        r"^kg.*phosphat.*$": "kg PO4 eq",
        
        # NMVOC equivalents
        r"^kg.*n.*mvoc.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg NMVOC eq",
        r"^kg.*nmvoc.*$": "kg NMVOC eq",
        
        # Ethene/Ethylene equivalents
        r"^kg.*(?:ethen|ethene|ethylen).*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg C2H2 eq",
        r"^kg.*(?:ethen|ethene|ethylen)[- ]?äq.*$": "kg C2H2 eq",
        r"^kg.*c2h[24].*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg C2H2 eq",
        
        # Antimony equivalents
        r"^kg.*sb.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg Sb eq",
        
        # Sulfur dioxide equivalents
        r"^kg.*so.*?2.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg SO2 eq",
        r"^kg.*so_?\(?2\)?.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg SO2 eq",
        
        # Phosphate equivalents
        r"^kg.*po.*?4.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg PO4 eq",
        r"^kg.*po_?\(?4\)?.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg PO4 eq",
        r"^kg.*po.*\(?3-?\)?.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg PO4 eq",
        r"^kg.*\(po4\)3-.*$": "kg PO4 eq",
        r"^kg.*phosphate.*$": "kg PO4 eq",
        
        # Nitrogen equivalents
        r"^kg.*n.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kg N eq",
        r"^mol.*n.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "mol N eq",
        r"^mole.*n.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "mol N eq",
        
        # Hydrogen ion equivalents
        r"^mol.*h.*[\+\^].*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "mol H+ eq",
        r"^mole.*h.*[\+\^].*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "mol H+ eq",
        r"^mol.*h.*[-\+](?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "mol H+ eq",
        
        # Uranium equivalents
        r"^k?bq.*u235.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*$": "kBq U235 eq",
        
        # World water equivalents
        r"^m.*?3.*world.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*(?:deprived|entzogen)?$": "m3 world eq deprived",
        r"^m\^?\(?3\)?.*w(?:orld|elt).*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\s?equivalent).*(?:deprived|entzogen)$": "m3 world eq deprived",
        
        # Disease incidence
        r"^disease\s*incidence$": "disease incidence",
        r"^krankheitsfälle$": "disease incidence",
        
        # Other specific units
        r"^ctuh$": "CTUh",
        r"^ctue$": "CTUe",
        r"^sqp$": "SQP",
        r"^dimensionless$": "dimensionless",
        
        # Simple units
        r"^-?$": "-",
        r"^mj$": "MJ",
        r"^kg$": "kg",
        
        # Per unit conversions
        r"^kg\/pce$": "kg/pce",
        r"^kg\s*\/\s*pce$": "kg/pce",
        
        # Compound units with divisions or per - volume-based
        r"^kg\s*\/\s*m[\^]?3$": "kg/m3",
        r"^kg\s*\/\s*m3$": "kg/m3",
        r"^kg\s*per\s*m3$": "kg/m3",
        r"^kg\s*per\s*m[\^]?3$": "kg/m3",
        
        # Compound units with divisions or per - area-based
        r"^kg\s*\/\s*m[\^]?2$": "kg/m2",
        r"^kg\s*\/\s*m2$": "kg/m2",
        r"^kg\s*per\s*m2$": "kg/m2",
        r"^kg\s*per\s*m[\^]?2$": "kg/m2"
    }

    for pattern, standard in mappings.items():
        if re.match(pattern, unit):
            return standard
    
    if unit not in not_found_units:
        print(f"Unit '{unit}' not found in standard mappings.")
        not_found_units.append(unit)
    return unit

def connect_to_db():
    """Connect to the PostgreSQL database and return the connection."""
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", "5432")
    )
    return conn

def get_products(conn):
    """Get products with process_id, name_en, and category levels."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            process_id, 
            name_en, 
            category_level_1, 
            category_level_2, 
            category_level_3
        FROM 
            products
    """)
    products = cursor.fetchall()
    cursor.close()
    
    # Convert to DataFrame
    products_df = pd.DataFrame(products, columns=[
        'process_id', 'name_en', 'category_level_1', 
        'category_level_2', 'category_level_3'
    ])
    
    return products_df

def get_lcia_data(conn):
    """Get LCIA results and module amounts."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            lr.process_id,
            lr.indicator_key,
            lr.unit,
            lma.module,
            lma.scenario,
            lma.amount
        FROM 
            lcia_results lr
        JOIN 
            lcia_moduleamounts lma ON lr.lcia_id = lma.lcia_id
    """)
    lcia_data = cursor.fetchall()
    cursor.close()
    
    # Convert to DataFrame
    lcia_df = pd.DataFrame(lcia_data, columns=[
        'process_id', 'indicator_key', 'unit', 
        'module', 'scenario', 'amount'
    ])

    # Normalize unit values
    lcia_df['unit'] = lcia_df['unit'].apply(normalize_unit)

    # Add type column to identify as LCIA
    lcia_df['type'] = 'lcia'
    
    return lcia_df

def get_exchange_data(conn):
    """Get exchanges and module amounts."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            e.process_id,
            e.indicator_key,
            e.unit,
            ema.module,
            ema.scenario,
            ema.amount
        FROM 
            exchanges e
        JOIN 
            exchange_moduleamounts ema ON e.exchange_id = ema.exchange_id
    """)
    exchange_data = cursor.fetchall()
    cursor.close()
    
    # Convert to DataFrame
    exchange_df = pd.DataFrame(exchange_data, columns=[
        'process_id', 'indicator_key', 'unit', 
        'module', 'scenario', 'amount'
    ])

    # Normalize unit values
    exchange_df['unit'] = exchange_df['unit'].apply(normalize_unit)

    # Add type column to identify as exchange
    exchange_df['type'] = 'exchange'
    
    return exchange_df

def get_material_properties(conn):
    """Get material properties and prepare them for normalization with indexed naming."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            process_id,
            property_name,
            value,
            units,
            description
        FROM 
            material_properties
    """)
    material_prop_data = cursor.fetchall()
    cursor.close()
    
    # Convert to DataFrame
    material_prop_df = pd.DataFrame(material_prop_data, columns=[
        'process_id', 'property_name', 'value', 'units', 'description'
    ])
    
    # Convert value column to numeric if possible
    material_prop_df['value'] = pd.to_numeric(material_prop_df['value'], errors='coerce')
    
    # Normalize units values
    material_prop_df['units'] = material_prop_df['units'].apply(normalize_unit)
    
    # Create indexed material property columns
    processed_material_props = {}
    
    # Group by process_id
    for process_id, group in material_prop_df.groupby('process_id'):
        prop_count = 1
        
        # For each material property in the process
        for _, row in group.iterrows():
            material_prop_prefix = f"material_prop_{prop_count}"
            
            # Initialize dict for this process_id if needed
            if process_id not in processed_material_props:
                processed_material_props[process_id] = {}
            
            # Store all material property attributes with indexed naming
            processed_material_props[process_id][f"property_name_{material_prop_prefix}"] = row['property_name']
            processed_material_props[process_id][f"value_{material_prop_prefix}"] = row['value']
            processed_material_props[process_id][f"units_{material_prop_prefix}"] = row['units']
            processed_material_props[process_id][f"description_{material_prop_prefix}"] = row['description']
            
            prop_count += 1
    
    # Convert dictionary to DataFrame
    material_prop_result_df = pd.DataFrame.from_dict(processed_material_props, orient='index')
    material_prop_result_df.reset_index(inplace=True)
    material_prop_result_df.rename(columns={'index': 'process_id'}, inplace=True)
    
    # Also create a DataFrame with the original material properties info for reference
    material_prop_df['material_prop_info'] = material_prop_df.apply(
        lambda row: f"{row['property_name']}: {row['value']} {row['units']} - {row['description']}",
        axis=1
    )
    
    material_prop_info = material_prop_df.groupby('process_id')['material_prop_info'].apply(
        lambda x: '; '.join(x)
    ).reset_index()
    
    return material_prop_result_df, material_prop_info

def main():
    # Connect to the database
    conn = connect_to_db()
    
    try:
        # Get all required data
        products_df = get_products(conn)
        lcia_df = get_lcia_data(conn)
        exchange_df = get_exchange_data(conn)
        
        # Get material properties with indexed naming and original format
        material_prop_df, material_prop_info = get_material_properties(conn)
        
        # Combine LCIA and exchange data
        combined_data = pd.concat([lcia_df, exchange_df])
        
        # Merge with products data
        result = pd.merge(
            combined_data, 
            products_df,
            on='process_id',
            how='left'
        )
        
        # Merge with indexed material properties data
        result = pd.merge(
            result,
            material_prop_df,
            on='process_id',
            how='left'
        )
        
        # Create normalized amount columns for each material property
        material_prop_indices = set()
        material_prop_columns = []
        
        # Identify all material property indices (material_prop_1, material_prop_2, etc.)
        for col in result.columns:
            if col.startswith('value_material_prop_'):
                material_prop_idx = col.split('value_')[1]  # Gets "material_prop_X"
                material_prop_indices.add(material_prop_idx)
                material_prop_columns.append(col)
        
        # Sort the material property indices to ensure consistent ordering
        material_prop_indices = sorted(list(material_prop_indices))
        
        # Create normalized columns for each material property
        for material_prop_idx in material_prop_indices:
            value_col = f"value_{material_prop_idx}"
            if value_col in result.columns:
                # Create normalized amount column
                result[f"normalized_amount_{material_prop_idx}"] = result['amount'] / result[value_col]
                
                # Create normalized unit column (combining the indicator unit with property unit)
                result[f"normalized_unit_{material_prop_idx}"] = result.apply(
                    lambda row: f"{row['unit']} / {row.get(f'units_{material_prop_idx}', '')}",
                    axis=1
                )
        
        # Define the base columns
        base_columns = [
            'process_id', 'name_en', 'category_level_1', 'category_level_2', 'category_level_3',
            'type', 'indicator_key', 'module', 'scenario', 'amount', 'unit'
        ]
        
        # Create a list to collect all material property-related columns in order
        material_prop_columns = []
        for material_prop_idx in material_prop_indices:
            # Add columns for this material property in the specified order
            material_prop_columns.extend([
                f"normalized_amount_{material_prop_idx}",
                f"normalized_unit_{material_prop_idx}",
                f"property_name_{material_prop_idx}",
                f"value_{material_prop_idx}",
                f"units_{material_prop_idx}",
                f"description_{material_prop_idx}"
            ])
        
        # Combine all columns
        final_columns = base_columns + material_prop_columns
        
        # Create the final result with only columns that exist
        existing_columns = [col for col in final_columns if col in result.columns]
        final_result = result[existing_columns]
        
        # Export to CSV
        output_file = 'product_data_with_normalized_amounts.csv'
        final_result.to_csv(output_file, index=False)
        
        print(f"Data successfully exported to {output_file}")
        print(f"Created normalized columns for material properties: {material_prop_indices}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()