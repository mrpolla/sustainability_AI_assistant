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
    """Get materials and concatenate them for each process_id."""
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
    
    # Create concatenated string for each material entry
    materials_df['material_info'] = materials_df.apply(
        lambda row: f"{row['property_name']}: {row['value']} {row['units']} - {row['description']}",
        axis=1
    )
    
    # Group by process_id and concatenate all material info
    materials_grouped = materials_df.groupby('process_id')['material_info'].apply(
        lambda x: '; '.join(x)
    ).reset_index()
    
    return materials_grouped

def main():
    # Connect to the database
    conn = connect_to_db()
    
    try:
        # Get all required data
        products_df = get_products(conn)
        lcia_df = get_lcia_data(conn)
        exchange_df = get_exchange_data(conn)
        materials_df = get_materials(conn)
        
        # Combine LCIA and exchange data
        combined_data = pd.concat([lcia_df, exchange_df])
        
        # Merge with products data
        result = pd.merge(
            combined_data, 
            products_df,
            on='process_id',
            how='left'
        )
        
        # Add materials information
        result = pd.merge(
            result,
            materials_df,
            on='process_id',
            how='left'
        )
        
        # Reorder columns to match the required output format
        final_result = result[[
            'process_id', 'name_en', 'category_level_1', 'category_level_2', 'category_level_3',
            'type', 'indicator_key', 'module', 'scenario', 'amount', 'unit', 'material_info'
        ]]
        
        # Export to CSV
        output_file = 'product_data_export.csv'
        final_result.to_csv(output_file, index=False)
        
        print(f"Data successfully exported to {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()