import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables from .env file (for database credentials)
load_dotenv()

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
    
    # Add type column to identify as exchange
    exchange_df['type'] = 'exchange'
    
    return exchange_df

def get_materials(conn):
    """Get materials and prepare them for normalization with indexed naming."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            process_id,
            property_name,
            value,
            units,
            description
        FROM 
            materials
    """)
    materials_data = cursor.fetchall()
    cursor.close()
    
    # Convert to DataFrame
    materials_df = pd.DataFrame(materials_data, columns=[
        'process_id', 'property_name', 'value', 'units', 'description'
    ])
    
    # Convert value column to numeric if possible
    materials_df['value'] = pd.to_numeric(materials_df['value'], errors='coerce')
    
    # Create a dictionary to store the processed materials data
    processed_materials = {}
    
    # Group by process_id
    for process_id, group in materials_df.groupby('process_id'):
        material_count = 1
        
        # For each material in the process
        for _, row in group.iterrows():
            material_prefix = f"material_{material_count}"
            
            # Initialize dict for this process_id if needed
            if process_id not in processed_materials:
                processed_materials[process_id] = {}
            
            # Store all material properties with indexed naming
            processed_materials[process_id][f"property_name_{material_prefix}"] = row['property_name']
            processed_materials[process_id][f"value_{material_prefix}"] = row['value']
            processed_materials[process_id][f"units_{material_prefix}"] = row['units']
            processed_materials[process_id][f"description_{material_prefix}"] = row['description']
            
            material_count += 1
    
    # Convert dictionary to DataFrame
    materials_result_df = pd.DataFrame.from_dict(processed_materials, orient='index')
    materials_result_df.reset_index(inplace=True)
    materials_result_df.rename(columns={'index': 'process_id'}, inplace=True)
    
    # Also create a DataFrame with the original materials info for reference
    materials_df['material_info'] = materials_df.apply(
        lambda row: f"{row['property_name']}: {row['value']} {row['units']} - {row['description']}",
        axis=1
    )
    
    materials_info = materials_df.groupby('process_id')['material_info'].apply(
        lambda x: '; '.join(x)
    ).reset_index()
    
    return materials_result_df, materials_info

def main():
    # Connect to the database
    conn = connect_to_db()
    
    try:
        # Get all required data
        products_df = get_products(conn)
        lcia_df = get_lcia_data(conn)
        exchange_df = get_exchange_data(conn)
        
        # Get materials with indexed naming and original format
        materials_df, materials_info = get_materials(conn)
        
        # Combine LCIA and exchange data
        combined_data = pd.concat([lcia_df, exchange_df])
        
        # Merge with products data
        result = pd.merge(
            combined_data, 
            products_df,
            on='process_id',
            how='left'
        )
        
        # Merge with indexed materials data
        result = pd.merge(
            result,
            materials_df,
            on='process_id',
            how='left'
        )
        
        # Create normalized amount columns for each material
        material_indices = set()
        material_columns = []
        
        # Identify all material indices (material_1, material_2, etc.)
        for col in result.columns:
            if col.startswith('value_material_'):
                material_idx = col.split('value_')[1]  # Gets "material_X"
                material_indices.add(material_idx)
                material_columns.append(col)
        
        # Sort the material indices to ensure consistent ordering
        material_indices = sorted(list(material_indices))
        
        # Create normalized columns for each material
        for material_idx in material_indices:
            value_col = f"value_{material_idx}"
            if value_col in result.columns:
                # Create normalized amount column
                result[f"normalized_amount_{material_idx}"] = result['amount'] / result[value_col]
                
                # Create normalized unit column (combining the indicator unit with material unit)
                result[f"normalized_unit_{material_idx}"] = result.apply(
                    lambda row: f"{row['unit']} / {row.get(f'units_{material_idx}', '')}",
                    axis=1
                )
        
        # Define the base columns
        base_columns = [
            'process_id', 'name_en', 'category_level_1', 'category_level_2', 'category_level_3',
            'type', 'indicator_key', 'module', 'scenario', 'amount', 'unit'
        ]
        
        # Create a list to collect all material-related columns in order
        material_columns = []
        for material_idx in material_indices:
            # Add columns for this material in the specified order
            material_columns.extend([
                f"normalized_amount_{material_idx}",
                f"normalized_unit_{material_idx}",
                f"property_name_{material_idx}",
                f"value_{material_idx}",
                f"units_{material_idx}",
                f"description_{material_idx}"
            ])
        
        # Combine all columns
        final_columns = base_columns + material_columns
        
        # Create the final result with only columns that exist
        existing_columns = [col for col in final_columns if col in result.columns]
        final_result = result[existing_columns]
        
        # Export to CSV
        output_file = 'product_data_with_normalized_amounts.csv'
        final_result.to_csv(output_file, index=False)
        
        print(f"Data successfully exported to {output_file}")
        print(f"Created normalized columns for materials: {material_indices}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()