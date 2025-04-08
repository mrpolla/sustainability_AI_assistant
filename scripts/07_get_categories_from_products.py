import json
import psycopg2
import os
import csv
from dotenv import load_dotenv
from helper_scripts.llm_utils import query_llm

# Load environment variables
load_dotenv()

# Configuration
TRANSLATIONS_FILE = "./translations/translations.csv"  # <-- Set your translations filename here
# "mistral",
# "llama3",
# "gemma:2b",
#" "qwen:1.8b",
#" "phi3:mini",
LLM_MODEL = "qwen:1.8b"

# DB connection settings
DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

def load_translations(csv_file=TRANSLATIONS_FILE):
    """Load German to English translations from CSV file"""
    translations = {}
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                if len(row) >= 2:  # Ensure the row has at least 2 columns (German, English)
                    german_text = row[0].strip()
                    english_text = row[1].strip()
                    if german_text and english_text:
                        translations[german_text] = english_text
        print(f"Loaded {len(translations)} translations from {csv_file}")
    except FileNotFoundError:
        print(f"Warning: Translations file '{csv_file}' not found. No translations will be applied.")
    
    return translations

def load_translations(csv_file=TRANSLATIONS_FILE):
    """Load German to English translations from CSV file"""
    translations = {}
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                if len(row) >= 2:  # Ensure the row has at least 2 columns (German, English)
                    german_text = row[0].strip()
                    english_text = row[1].strip()
                    if german_text and english_text:
                        translations[german_text] = english_text
        print(f"Loaded {len(translations)} translations from {csv_file}")
    except FileNotFoundError:
        print(f"Warning: Translations file '{csv_file}' not found. No translations will be applied.")
    
    return translations

not_found_translations = []
def translate_text(text, translations):
    """Translate text from German to English if a translation exists"""
    formatted_text = text.replace(",", "").tolower().trim()
    if formatted_text not in translations:
        print(f"Warning: Translations for  '{text}' not found.")
        if text not in not_found_translations:
            not_found_translations.append(text)
        return text

    return translations.get(text) # Return original if no translation found

def get_classifications_by_process_id(conn, process_id, translations=None):
    """Retrieve all classifications for a specific process_id with translations"""
    cur = conn.cursor()
    cur.execute("""
        SELECT level, classification, name 
        FROM classifications 
        WHERE process_id = %s
        ORDER BY level
    """, (process_id,))
    results = cur.fetchall()
    cur.close()
    
    # Organize classifications by level
    classifications = {
        "0": [],
        "1": [],
        "2": []
    }
    
    for level, classification, name in results:
        # Apply translations only to classification text if available
        if translations:
            classification_en = translate_text(classification, translations)
        else:
            classification_en = classification
            
        classifications[level].append({
            "classification": classification,
            "classification_en": classification_en,
            "name": name
        })
    
    return classifications

def generate_llm_prompts(product, classifications):
    """Generate prompts for the LLM using translated content"""
    # Combine product data with classifications for context
    context = f"""
Product Name: {product['name_en']}
Description: {product['description_en'] or 'N/A'}
Technical Description: {product['tech_descr_en'] or 'N/A'}

Classifications:
"""

    # Add classification information (using translated version if available)
    for level in ["0", "1", "2"]:
        if classifications[level]:
            context += f"Level {level}:\n"
            for cls in classifications[level]:
                # Use the original name and the English translation for classification
                name = cls['name']
                classification = cls.get('classification_en', cls['classification'])
                context += f"- {name}: {classification}\n"

    # Materials prompt
    materials_prompt = f"""{context}

Based on the information above, what materials is this product likely made from?
Be very concise - list only the main materials, maximum 4-5 items.

Example format:
- Concrete
- Steel
- Glass
- Aluminum"""

    # Uses prompt
    uses_prompt = f"""{context}

Based on the information above, what would be the primary uses of this product in a construction environment?
Be very concise - list up to 3 specific applications or use cases in short bullet points.

Example format:
- Interior wall construction
- Sound insulation
- Fire protection"""

    return {
        "materials_prompt": materials_prompt,
        "uses_prompt": uses_prompt
    }

def main():
    # Load translations
    translations = load_translations()
    
    # Connect to the database
    conn = psycopg2.connect(**DB_PARAMS)
    
    try:
        # Get all products with required fields
        cur = conn.cursor()
        cur.execute("""
            SELECT process_id, name_en, description_en, tech_descr_en 
            FROM products
        """)
        products = cur.fetchall()
        cur.close()
        
        results = []
        
        # Process each product
        for i, (process_id, name_en, description_en, tech_descr_en) in enumerate(products):
            print(f"Processing product {i+1}/{len(products)}: {name_en}")
            
            # Get classifications for this product with translations
            classifications = get_classifications_by_process_id(conn, process_id, translations)

            # Create product object
            product = {
                "process_id": process_id,
                "name_en": name_en,
                "description_en": description_en,
                "tech_descr_en": tech_descr_en
            }
            
            # Generate prompts
            prompts = generate_llm_prompts(product, classifications)
            
            # Query LLM for each prompt
            print(f"  > Querying LLM for materials...")
            materials_response = query_llm(prompts["materials_prompt"], LLM_MODEL)
            
            print(f"  > Querying LLM for uses...")
            uses_response = query_llm(prompts["uses_prompt"], LLM_MODEL)
            
            # Store results
            result = {
                "process_id": process_id,
                "name": name_en,
                "classifications": classifications,
                "llm_analysis": {
                    "probable_materials": materials_response.strip(),
                    "construction_uses": uses_response.strip()
                },
                "translations_applied": bool(translations)
            }
            
            results.append(result)
            
            # Optional: save intermediate results in case of failure
            if (i + 1) % 10 == 0:
                with open(f"products_analysis_checkpoint_{i+1}.json", "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save final results
        with open("products_analysis_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        with open("translations_not_found.txt", "w", encoding="utf-8") as f:
            for item in not_found_translations:
                f.write(f"{item}\n")

        print(f"Analysis completed for {len(results)} products. Results saved to products_analysis_results.json")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()