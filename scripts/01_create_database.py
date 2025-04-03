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

def create_database_and_tables():
    """Creates the database and tables needed for the EPD data."""

    try:
        # Connect to the PostgreSQL server (without specifying the database)
        conn = psycopg2.connect(**DB_PARAMS)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT) #important for database creation

        cur = conn.cursor()

        # Check if the database already exists
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'")
        exists = cur.fetchone()

        if not exists:
            # Create the database if it doesn't exist
            cur.execute(f"CREATE DATABASE {DB_NAME}")
            logger.info(f"Database '{DB_NAME}' created successfully.")
        else:
            logger.info(f"Database '{DB_NAME}' already exists.")

        # Close the initial connection
        cur.close()
        conn.close()

        # Connect to the newly created database
        conn = psycopg2.connect(dbname=DB_NAME, **DB_PARAMS)
        cursor = conn.cursor()

        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Products (
                process_id TEXT PRIMARY KEY,
                uuid TEXT,
                version TEXT,
                name_en TEXT,
                name_de TEXT,
                description_de TEXT,
                description_en TEXT,
                reference_year TEXT,
                valid_until TEXT,
                time_repr_de TEXT,
                time_repr_en TEXT,
                safety_margin TEXT,
                safety_descr_de TEXT,
                safety_descr_en TEXT,
                geo_location TEXT,
                geo_descr_de TEXT,
                geo_descr_en TEXT,
                tech_descr_de TEXT,
                tech_descr_en TEXT,
                tech_applic_de TEXT,
                tech_applic_en TEXT,
                dataset_type TEXT,
                dataset_subtype TEXT,
                sources TEXT,
                use_advice_de TEXT,
                use_advice_en TEXT,
                generator_de TEXT,
                generator_en TEXT,
                entry_by_de TEXT,
                entry_by_en TEXT,
                admin_version TEXT,
                license_type TEXT,
                access_de TEXT,
                access_en TEXT,
                timestamp TIMESTAMP,
                formats TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Compliances (
                compliance_id SERIAL PRIMARY KEY,
                process_id TEXT,
                system_de TEXT,
                system_en TEXT,
                approval TEXT,
                FOREIGN KEY (process_id) REFERENCES Products (process_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Classifications (
                process_id TEXT,
                name TEXT,
                level TEXT,
                classId TEXT,
                classification TEXT,
                FOREIGN KEY (process_id) REFERENCES Products (process_id) ON DELETE CASCADE
            )
        ''')    

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Exchanges (
                exchange_id SERIAL PRIMARY KEY,
                process_id TEXT,
                flow_de TEXT,
                flow_en TEXT,
                indicator_key TEXT,
                direction TEXT,
                meanAmount REAL,
                unit TEXT,
                FOREIGN KEY (process_id) REFERENCES Products (process_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Exchange_ModuleAmounts (
                module_amount_id SERIAL PRIMARY KEY,
                exchange_id INTEGER,
                module TEXT,
                scenario TEXT,
                amount REAL,
                FOREIGN KEY (exchange_id) REFERENCES Exchanges (exchange_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS LCIA_Results (
                lcia_id SERIAL PRIMARY KEY,
                process_id TEXT,
                method_de TEXT,
                method_en TEXT,
                indicator_key TEXT,
                meanAmount REAL,
                unit TEXT,
                FOREIGN KEY (process_id) REFERENCES Products (process_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS LCIA_ModuleAmounts (
                lcia_module_amount_id SERIAL PRIMARY KEY,
                lcia_id INTEGER,
                module TEXT,
                scenario TEXT,
                amount REAL,
                FOREIGN KEY (lcia_id) REFERENCES LCIA_Results (lcia_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Reviews (
                review_id SERIAL PRIMARY KEY,
                process_id TEXT,
                reviewer TEXT,
                detail_de TEXT,
                detail_en TEXT,
                FOREIGN KEY (process_id) REFERENCES Products (process_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Materials (
                material_id SERIAL PRIMARY KEY,
                process_id TEXT,
                property_id TEXT,
                property_name TEXT,
                value REAL,
                units TEXT,
                description TEXT,
                FOREIGN KEY (process_id) REFERENCES Products (process_id) ON DELETE CASCADE
            )
        ''')

        conn.commit()
        logger.info("Tables created successfully.")

    except psycopg2.Error as e:
        logger.error(f"Error creating database or tables: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    create_database_and_tables()
