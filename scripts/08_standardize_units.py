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
    """Get materials and prepare them for normalization."""
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
    
    # Create a pivot table: process_id as index, property_name as columns, value as values
    pivoted_materials = materials_df.pivot_table(
        index='process_id',
        columns='property_name',
        values='value',
        aggfunc='first'  # In case of duplicates, take the first value
    ).reset_index()
    
    # Also create a DataFrame with the original materials info for reference
    materials_df['material_info'] = materials_df.apply(
        lambda row: f"{row['property_name']}: {row['value']} {row['units']} - {row['description']}",
        axis=1
    )
    
    materials_info = materials_df.groupby('process_id')['material_info'].apply(
        lambda x: '; '.join(x)
    ).reset_index()
    
    return pivoted_materials, materials_info

def main():
    # Connect to the database
    conn = connect_to_db()
    
    try:
        # Get all required data
        products_df = get_products(conn)
        lcia_df = get_lcia_data(conn)
        exchange_df = get_exchange_data(conn)
        
        # Get material values in pivot format and original format
        pivoted_materials, materials_info = get_materials(conn)
        
        # Combine LCIA and exchange data
        combined_data = pd.concat([lcia_df, exchange_df])
        
        # Merge with products data
        result = pd.merge(
            combined_data, 
            products_df,
            on='process_id',
            how='left'
        )
        
        # Add original materials information
        result = pd.merge(
            result,
            materials_info,
            on='process_id',
            how='left'
        )
        
        # Merge with pivoted materials
        result = pd.merge(
            result,
            pivoted_materials,
            on='process_id',
            how='left'
        )
        
        # Create normalized columns for each material property
        material_properties = [col for col in pivoted_materials.columns if col != 'process_id']
        for prop in material_properties:
            result[f'normalized_by_{prop}'] = result['amount'] / result[prop]
        
        # Reorder columns to include the new normalized columns
        # First get the base columns
        base_columns = [
            'process_id', 'name_en', 'category_level_1', 'category_level_2', 'category_level_3',
            'type', 'indicator_key', 'module', 'scenario', 'amount', 'unit', 'material_info'
        ]
        
        # Add the material property columns and normalized columns
        normalized_columns = [f'normalized_by_{prop}' for prop in material_properties]
        
        # Combine all columns
        final_columns = base_columns + material_properties + normalized_columns
        
        # Create the final result with all columns (that exist in the result DataFrame)
        existing_columns = [col for col in final_columns if col in result.columns]
        final_result = result[existing_columns]
        
        # Export to CSV
        output_file = 'product_data_with_normalized_amounts.csv'
        final_result.to_csv(output_file, index=False)
        
        print(f"Data successfully exported to {output_file}")
        print(f"Created normalized columns: {normalized_columns}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()