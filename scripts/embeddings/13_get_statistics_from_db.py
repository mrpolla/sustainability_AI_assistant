import os
import psycopg2
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

def connect_to_db():
    return psycopg2.connect(**DB_PARAMS)

def create_statistics_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS indicator_statistics (
            stat_id SERIAL PRIMARY KEY,
            category_level_1 TEXT,
            category_level_2 TEXT,
            category_level_3 TEXT,
            indicator_key TEXT,
            source TEXT,
            module TEXT,
            mean REAL,
            median REAL,
            std_dev REAL,
            min REAL,
            max REAL,
            unit TEXT,
            count INTEGER,
            last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
        );
        """)
        conn.commit()

def get_combined_data(conn):
    # Load LCIA data
    lcia_query = """
        SELECT lr.process_id, lr.indicator_key, lr.unit, lma.module, lma.amount, 'lcia' AS source
        FROM lcia_results lr
        JOIN lcia_moduleamounts lma ON lr.lcia_id = lma.lcia_id
    """
    lcia_df = pd.read_sql(lcia_query, conn)

    # Load exchange data
    exchange_query = """
        SELECT e.process_id, e.indicator_key, e.unit, ema.module, ema.amount, 'exchange' AS source
        FROM exchanges e
        JOIN exchange_moduleamounts ema ON e.exchange_id = ema.exchange_id
    """
    exchange_df = pd.read_sql(exchange_query, conn)

    # Load product categories
    products_query = """
        SELECT process_id, category_level_1, category_level_2, category_level_3
        FROM products
    """
    products_df = pd.read_sql(products_query, conn)

    # Combine and merge with product categories
    data = pd.concat([lcia_df, exchange_df], ignore_index=True)
    data = data.merge(products_df, on='process_id', how='left')
    return data

def calculate_and_store_statistics(conn, data):
    def insert_stats(grouped_df):
        with conn.cursor() as cur:
            for _, row in grouped_df.iterrows():
                cur.execute("""
                    INSERT INTO indicator_statistics (
                        category_level_1, category_level_2, category_level_3,
                        indicator_key, source, module,
                        mean, median, std_dev, min, max, unit, count
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    row.get('category_level_1'),
                    row.get('category_level_2'),
                    row.get('category_level_3'),
                    row['indicator_key'], row['source'], row['module'],
                    row['mean'], row['median'], row['std'], row['min'], row['max'], row['unit'], int(row['count'])
                ))
            conn.commit()

    # Stats for level 3
    group3 = data.groupby([
        'category_level_1', 'category_level_2', 'category_level_3', 
        'indicator_key', 'source', 'module', 'unit'])['amount']
    stats3 = group3.agg(['mean', 'median', 'std', 'min', 'max', 'count']).reset_index()
    insert_stats(stats3)

    # Stats for level 2
    group2 = data.groupby([
        'category_level_1', 'category_level_2', 
        'indicator_key', 'source', 'module', 'unit'])['amount']
    stats2 = group2.agg(['mean', 'median', 'std', 'min', 'max', 'count']).reset_index()
    stats2['category_level_3'] = None
    insert_stats(stats2)

    # Stats for level 1
    group1 = data.groupby([
        'category_level_1', 
        'indicator_key', 'source', 'module', 'unit'])['amount']
    stats1 = group1.agg(['mean', 'median', 'std', 'min', 'max', 'count']).reset_index()
    stats1['category_level_2'] = None
    stats1['category_level_3'] = None
    insert_stats(stats1)

def main():
    conn = connect_to_db()
    try:
        create_statistics_table(conn)
        data = get_combined_data(conn)
        calculate_and_store_statistics(conn, data)
        print("Statistics successfully stored in the database.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
