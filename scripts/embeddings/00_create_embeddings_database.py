import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='database_setup.log')
logger = logging.getLogger(__name__)

# Get database connection parameters from .env
DB_NAME = os.getenv("DB_NAME")
DB_PARAMS = {
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'host': os.getenv("DB_HOST"),
    'port': os.getenv("DB_PORT")
}
EMBEDDING_DIM = 384  # For bge-small-en-v1.5

def create_database_and_tables():
    """Creates the database, extensions, and tables needed for the EPD data."""

    try:
        # Reconnect to the new database
        conn = psycopg2.connect(dbname=DB_NAME, **DB_PARAMS)
        cur = conn.cursor()

        # Enable pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        logger.info("pgvector extension enabled.")

        # === Create Embeddings Table ===
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT PRIMARY KEY,
                process_id TEXT,
                embedding VECTOR({EMBEDDING_DIM}),
                chunk TEXT,
                metadata JSONB,
                FOREIGN KEY (process_id) REFERENCES Products (process_id) ON DELETE CASCADE
            );
        ''')

        conn.commit()
        logger.info("Embeddings tables created successfully.")

    except psycopg2.Error as e:
        logger.error(f"Error creating database or tables: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    create_database_and_tables()
