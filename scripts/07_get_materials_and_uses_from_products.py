import json
import psycopg2
import os
import csv
import argparse
import time
import re
from datetime import datetime
from dotenv import load_dotenv
from helper_scripts.llm_utils import query_llm

# Load environment variables
load_dotenv()

# Configuration
TRANSLATIONS_FILE = "./translations/translations.csv"  # <-- Set your translations filename here
DEFAULT_LLM_MODEL = "nuextract"  # Default model
# mistral
# llama3
# gemma:2b
# qwen:1.8b
# phi3:mini
# winkefinger/alma-13b  - good for translation
# zongwei/gemma3-translator:1b  - good for translation
# nuextract  - good for text extraction
MAX_PRODUCTS = 200  # Limit to 200 products

# Output folder for logs and results
OUTPUT_FOLDER = "./logs/07_get_categories_from_products"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

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
                        translations[german_text.lower()] = english_text
        print(f"Loaded {len(translations)} translations from {csv_file}")
    except FileNotFoundError:
        print(f"Warning: Translations file '{csv_file}' not found. No translations will be applied.")
    
    return translations

not_found_translations = []
def translate_text(text, translations):
    """Translate text from German to English if a translation exists"""
    if not text:
        return text
        
    formatted_text = text.replace(",", "").lower().strip()
    if formatted_text not in translations:
        print(f"Warning: Translation for '{text}' not found.")
        if text not in not_found_translations:
            not_found_translations.append(text)
        return text

    return translations.get(formatted_text, text)  # Return original if no translation found

def extract_categories_from_product(product):
    """Extract category information directly from product fields"""
    # Initialize the categories
    categories = []
    
    # Add each category level if available
    if product.get('category_level_1'):
        categories.append(product['category_level_1'])
        
    if product.get('category_level_2'):
        categories.append(product['category_level_2'])
        
    if product.get('category_level_3'):
        categories.append(product['category_level_3'])
    
    return categories

def translate_german_fields(product, model, log_file=None):
    """
    Translate German fields to English using the LLM when English versions are missing
    """
    translated_product = product.copy()
    
    # Fields that need translation if English version is missing
    fields_to_translate = [
        ('name_en', 'name_de'),
        ('description_en', 'description_de'),
        ('tech_descr_en', 'tech_descr_de'),
        ('tech_applic_en', 'tech_applic_de')
    ]
    
    for en_field, de_field in fields_to_translate:
        # Only translate if English field is missing and German field exists
        if (not product[en_field] or product[en_field].strip() == '') and product[de_field]:
            # For short fields (like name), translate directly
            if len(product[de_field].split()) <= 30:
                prompt = f"""You are a construction industry translator specializing in technical terminology.
                
Translate this German construction product text to English with precise technical accuracy:

"{product[de_field]}"

Return only the translation, nothing else."""
                
                # Log the translation prompt if requested
                if log_file:
                    log_file.write(f"\n\n--- TRANSLATION PROMPT ({de_field} → {en_field}) ---\n")
                    log_file.write(prompt)
                
                translated_text = query_llm(prompt, model)
                
                # Log the translation response if requested
                if log_file:
                    log_file.write(f"\n\n--- TRANSLATION RESPONSE ---\n")
                    log_file.write(translated_text)
                
                translated_product[en_field] = translated_text.strip()
                print(f"  > Translated {de_field} to {en_field}: {translated_text[:40]}...")
            else:
                # For longer texts, extract key information while translating
                prompt = f"""You are a construction industry specialist translating technical product information.

Extract and translate the key information from this German construction product text:

"{product[de_field][:1500]}..."

Focus on extracting and accurately translating:
1. All specific materials mentioned (be as technical and precise as possible)
2. All specific construction applications mentioned
3. Key technical specifications and properties

Respond in English with complete sentences organized into clear sections."""
                
                # Log the extraction+translation prompt if requested
                if log_file:
                    log_file.write(f"\n\n--- EXTRACT+TRANSLATE PROMPT ({de_field} → {en_field}) ---\n")
                    log_file.write(prompt)
                
                summarized_text = query_llm(prompt, model)
                
                # Log the extraction+translation response if requested
                if log_file:
                    log_file.write(f"\n\n--- EXTRACT+TRANSLATE RESPONSE ---\n")
                    log_file.write(summarized_text)
                
                translated_product[en_field] = summarized_text.strip()
                print(f"  > Extracted key points from {de_field} to {en_field}: {summarized_text[:40]}...")
    
    return translated_product

def extract_materials(product, model, log_file=None):
    """
    Extract materials from product information with improved prompting
    """
    # Build context from product info - use AI translations as fallbacks
    product_name = product['name_en'] or product.get('name_en_ai', '') or product['name_de']
    tech_applic = product['tech_applic_en'] or product.get('tech_applic_en_ai', '')
    description = product['description_en'] or product.get('description_en_ai', '')
    tech_descr = product['tech_descr_en'] or product.get('tech_descr_en_ai', '')
    
    # Combine all relevant text fields for analysis
    combined_text = f"""
Product Name: {product_name}

Technical Application: {tech_applic}

Description: {description}

Technical Description: {tech_descr}
"""
    
    # Create the improved materials extraction prompt
    materials_prompt = f"""You are a constructions material specialist analyzing Environmental Product Declarations (EPDs).

Your task: Extract ONLY the physical materials this product is physically made from.

Analyze this construction product information carefully:

{combined_text}

MATERIALS INSTRUCTIONS:
- ONLY include physical materials present in the final, installed construction product
- DO NOT include life cycle modules (e.g., A1-A3, C3, D)
- DO NOT include manufacturing chemicals like cleaning agents unless they remain in the final product
- DO NOT include energy, emissions, waste, or processes
- DO NOT include package materials or temporary substances
- Be precise with material names (e.g., "high-density polyethylene" not just "plastic")
- Include technical specifications of materials when mentioned
- Focus on the main materials, not trace elements
- Include at least 3 materials if mentioned in the text
- Exclude substances used only during manufacturing that don't remain in the final product

RESPOND WITH ONLY a numbered list of materials in this exact format:
1. [First material]
2. [Second material]
3. [Third material]
...

DO NOT include any explanations, headers, or other text."""

    # Log the materials prompt if requested
    if log_file:
        log_file.write(f"\n\n--- MATERIALS EXTRACTION PROMPT ---\n")
        log_file.write(materials_prompt)
    
    # Query the LLM for materials extraction
    materials_response = query_llm(materials_prompt, model)
    
    # Log the materials response if requested
    if log_file:
        log_file.write(f"\n\n--- MATERIALS EXTRACTION RESPONSE ---\n")
        log_file.write(materials_response)
    
    # Parse the materials response
    materials = []
    for line in materials_response.split('\n'):
        line = line.strip()
        # Match lines starting with numbers or bullets
        if re.match(r'^\d+\.|\*|•|-', line):
            # Extract the material name, removing the number/bullet
            material = re.sub(r'^\d+\.|\*|•|-', '', line).strip()
            if material and material not in materials:
                materials.append(material)
    
    return materials

def extract_uses(product, model, log_file=None):
    """
    Extract uses/applications from product information with improved prompting
    """
    # Build context from product info - use AI translations as fallbacks
    product_name = product['name_en'] or product.get('name_en_ai', '') or product['name_de']
    tech_applic = product['tech_applic_en'] or product.get('tech_applic_en_ai', '')
    description = product['description_en'] or product.get('description_en_ai', '')
    tech_descr = product['tech_descr_en'] or product.get('tech_descr_en_ai', '')
    
    # Combine all relevant text fields for analysis
    combined_text = f"""
Product Name: {product_name}

Technical Application: {tech_applic}

Description: {description}

Technical Description: {tech_descr}
"""
    
    # Create the improved uses extraction prompt
    uses_prompt = f"""You are a construction applications specialist analyzing Environmental Product Declarations (EPDs).

Your task: Extract ONLY the specific construction applications where this product is used.

Analyze this construction product information carefully:

{combined_text}

USE CASE INSTRUCTIONS:
- Focus ONLY on how and where the product is actually used in construction
- Describe specific applications in buildings or structures
- Include building components where the product is installed
- Group similar applications into representative types
- DO NOT include manufacturing processes or life cycle phases
- DO NOT include very general categories
- Focus on 3-5 most important, specific applications
- Avoid redundancy by consolidating similar use cases
- Give precise, specific uses rather than vague categories
- Be concise but precise in describing each application

RESPOND WITH ONLY a numbered list of applications in this exact format:
1. [First application]
2. [Second application]
3. [Third application]
...

DO NOT include any explanations, headers, or other text."""

    # Log the uses prompt if requested
    if log_file:
        log_file.write(f"\n\n--- USES EXTRACTION PROMPT ---\n")
        log_file.write(uses_prompt)
    
    # Query the LLM for uses extraction
    uses_response = query_llm(uses_prompt, model)
    
    # Log the uses response if requested
    if log_file:
        log_file.write(f"\n\n--- USES EXTRACTION RESPONSE ---\n")
        log_file.write(uses_response)
    
    # Parse the uses response
    uses = []
    for line in uses_response.split('\n'):
        line = line.strip()
        # Match lines starting with numbers or bullets
        if re.match(r'^\d+\.|\*|•|-', line):
            # Extract the use case, removing the number/bullet
            use = re.sub(r'^\d+\.|\*|•|-', '', line).strip()
            if use and use not in uses:
                uses.append(use)
    
    return uses

def create_json_output(process_id, materials, uses):
    """
    Create JSON output directly from extracted materials and uses
    """
    json_obj = {
        "process_id": process_id,
        "materials": materials if materials else [],
        "uses": uses if uses else []
    }
    
    return json_obj

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract product information using LLMs')
    parser.add_argument('--model', type=str, default=DEFAULT_LLM_MODEL, 
                        help=f'LLM model to use (default: {DEFAULT_LLM_MODEL})')
    parser.add_argument('--max-products', type=int, default=MAX_PRODUCTS, 
                        help=f'Maximum number of products to process (default: {MAX_PRODUCTS})')
    parser.add_argument('--skip-translation', action='store_true', 
                        help='Skip translation of German fields')
    args = parser.parse_args()
    
    # Get selected model and create timestamp
    selected_model = args.model
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create log file for prompts and responses
    log_filename = os.path.join(OUTPUT_FOLDER, f"product_analysis_{selected_model}_{timestamp}.log")
    print(f"Creating log file for prompts and responses: {log_filename}")
    log_file = open(log_filename, "w", encoding="utf-8")
    log_file.write(f"PRODUCT ANALYSIS LOG - Model: {selected_model}, Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load translations
    translations = load_translations()
    
    # Connect to the database
    conn = psycopg2.connect(**DB_PARAMS)
    
    try:
        # Get all products with required fields, including category levels and AI-translated fields
        cur = conn.cursor()
        cur.execute("""
            SELECT process_id, 
                   name_en, name_de, name_en_ai,
                   description_en, description_de, description_en_ai, 
                   tech_descr_en, tech_descr_de, tech_descr_en_ai,
                   tech_applic_en, tech_applic_de, tech_applic_en_ai,
                   category_level_1, category_level_2, category_level_3
            FROM products
            LIMIT %s
        """, (args.max_products,))
        products = cur.fetchall()
        cur.close()
        
        results = []
        
        # Process each product
        for i, (process_id, name_en, name_de, name_en_ai, 
                description_en, description_de, description_en_ai, 
                tech_descr_en, tech_descr_de, tech_descr_en_ai, 
                tech_applic_en, tech_applic_de, tech_applic_en_ai,
                category_level_1, category_level_2, category_level_3) in enumerate(products):
            
            # Use English field or AI translation or German field for display name
            product_name = name_en or name_en_ai or name_de
            print(f"Processing product {i+1}/{len(products)}: {product_name}")
            log_file.write(f"\n\n{'='*80}\nPRODUCT {i+1}/{len(products)}: {product_name} (ID: {process_id})\n{'='*80}\n")
            
            # Create product object with all required fields including AI translations
            product = {
                "process_id": process_id,
                "name_en": name_en,
                "name_de": name_de,
                "name_en_ai": name_en_ai,
                "description_en": description_en,
                "description_de": description_de,
                "description_en_ai": description_en_ai,
                "tech_descr_en": tech_descr_en,
                "tech_descr_de": tech_descr_de,
                "tech_descr_en_ai": tech_descr_en_ai,
                "tech_applic_en": tech_applic_en,
                "tech_applic_de": tech_applic_de,
                "tech_applic_en_ai": tech_applic_en_ai,
                "category_level_1": category_level_1,
                "category_level_2": category_level_2,
                "category_level_3": category_level_3
            }
            
            # Extract categories from product data
            categories = extract_categories_from_product(product)
            
            # STEP 1: Translate German fields when English versions are missing (if not skipped)
            if not args.skip_translation:
                missing_english = any(not product[f] and not product[f+'_ai'] and product[g] for f, g in [
                    ('name_en', 'name_de'), 
                    ('description_en', 'description_de'),
                    ('tech_descr_en', 'tech_descr_de'),
                    ('tech_applic_en', 'tech_applic_de')
                ])
                
                if missing_english:
                    print(f"  > Translating missing English fields from German...")
                    log_file.write("\nTRANSLATING MISSING ENGLISH FIELDS\n")
                    product = translate_german_fields(product, selected_model, log_file)
            
            # STEP 2: Extract materials (separate query with improved prompt)
            print(f"  > Extracting materials...")
            start_time = time.time()
            materials = extract_materials(product, selected_model, log_file)
            materials_time = time.time() - start_time
            print(f"  > Materials extraction completed in {materials_time:.2f} seconds")
            print(f"  > Found {len(materials)} materials: {', '.join(materials[:3])}")
            
            # STEP 3: Extract uses (separate query with improved prompt)
            print(f"  > Extracting uses...")
            start_time = time.time()
            uses = extract_uses(product, selected_model, log_file)
            uses_time = time.time() - start_time
            print(f"  > Uses extraction completed in {uses_time:.2f} seconds")
            print(f"  > Found {len(uses)} uses: {', '.join(uses[:3])}")
            
            # STEP 4: Create JSON output directly
            json_obj = create_json_output(process_id, materials, uses)
            
            # Store results
            result = {
                "process_id": process_id,
                "name": product_name,
                "categories": categories,
                "llm_analysis": json_obj,
                "raw_extraction": {
                    "materials": materials,
                    "uses": uses
                },
                "translations_applied": not args.skip_translation,
                "materials_extraction_time_seconds": materials_time,
                "uses_extraction_time_seconds": uses_time,
                "total_time_seconds": materials_time + uses_time
            }
            
            results.append(result)
            
            # Save intermediate results after each product
            output_filename = os.path.join(OUTPUT_FOLDER, f"products_analysis_{selected_model}_{timestamp}.json")
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"  > Results saved to {output_filename}")
        
        # Save final results
        final_output = os.path.join(OUTPUT_FOLDER, f"products_analysis_{selected_model}_{timestamp}_final.json")
        with open(final_output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"Analysis completed for {len(results)} products. Final results saved to {final_output}")

        final_output_data = os.path.join("data", "materials_and_uses", "materials_and_uses.json")
        with open(final_output_data, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"Analysis completed for {len(results)} products. Final results saved to {final_output_data}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        log_file.write(f"\n\nERROR: {str(e)}")
    finally:
        conn.close()
        log_file.close()
        print(f"Log file closed: {log_filename}")

if __name__ == "__main__":
    main()