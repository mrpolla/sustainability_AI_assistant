import os
import psycopg2
import csv
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TRANSLATIONS_FILE = "./translations/translations.csv"

DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

def load_translations(csv_file=TRANSLATIONS_FILE):
    translations = {}
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    german = row[0].strip()
                    english = row[1].strip()
                    if german and english:
                        translations[german.lower()] = english
        print(f"Loaded {len(translations)} translations.")
    except FileNotFoundError:
        print(f"Translation file {csv_file} not found.")
    return translations

not_found_translations = []
def translate_text(text, translations):
    """Translate text from German to English if a translation exists"""
    cleaned_text = text.replace(",", "").lower().strip()
    if cleaned_text not in translations:
        print(f"Warning: Translations for  '{text}' not found.")
        if text not in not_found_translations:
            not_found_translations.append(text)
        return text

    return translations.get(cleaned_text) # Return original if no translation found

def get_classifications(conn, process_id):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT level, classification 
            FROM classifications 
            WHERE process_id = %s
            ORDER BY level
        """, (process_id,))
        return cur.fetchall()

def update_product_categories(conn, process_id, cat1, cat2, cat3):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE products
            SET category_level_1 = %s,
                category_level_2 = %s,
                category_level_3 = %s
            WHERE process_id = %s
        """, (cat1, cat2, cat3, process_id))

def main():
    translations = load_translations()
    conn = psycopg2.connect(**DB_PARAMS)

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT process_id FROM products")
            products = cur.fetchall()

        for (process_id,) in products:
            classifications = get_classifications(conn, process_id)

            cat_levels = {"0": None, "1": None, "2": None}
            for level, classification in classifications:
                translated = translate_text(classification, translations)
                if level in cat_levels and cat_levels[level] is None:
                    cat_levels[level] = translated

            update_product_categories(
                conn,
                process_id,
                cat_levels["0"],
                cat_levels["1"],
                cat_levels["2"]
            )

        conn.commit()
        print("Category levels updated in products table.")

        with open("translations_not_found.txt", "w", encoding="utf-8") as f:
            for item in not_found_translations:
                f.write(f"{item}\n")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
