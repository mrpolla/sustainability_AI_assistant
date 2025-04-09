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
# Available models:
# "mistral",
# "llama3",
# "gemma:2b",
# "qwen:1.8b",
# "phi3:mini",
DEFAULT_LLM_MODEL = "llama3"  # Default model
MAX_PRODUCTS = 10  # Limit to 10 products

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

def extract_categories_from_product(product, translations=None):
    """Extract category information directly from product fields"""
    # Initialize the categories structure
    categories = {
        "1": [],
        "2": [],
        "3": []
    }
    
    # Extract categories from product fields
    if product.get('category_level_1'):
        cat_value = product['category_level_1']
        # Apply translation if available
        cat_value_en = translate_text(cat_value, translations) if translations else cat_value
        categories["1"].append({
            "classification": cat_value,
            "classification_en": cat_value_en,
            "name": "Category Level 1"
        })
        
    if product.get('category_level_2'):
        cat_value = product['category_level_2']
        # Apply translation if available
        cat_value_en = translate_text(cat_value, translations) if translations else cat_value
        categories["2"].append({
            "classification": cat_value,
            "classification_en": cat_value_en,
            "name": "Category Level 2"
        })
        
    if product.get('category_level_3'):
        cat_value = product['category_level_3']
        # Apply translation if available
        cat_value_en = translate_text(cat_value, translations) if translations else cat_value
        categories["3"].append({
            "classification": cat_value,
            "classification_en": cat_value_en,
            "name": "Category Level 3"
        })
    
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

def extract_materials_and_uses(product, model, log_file=None):
    """
    First step of two-step approach: Extract materials and uses using a focused prompt
    """
    # Build context from product info
    product_name = product['name_en'] if product['name_en'] else product['name_de']
    tech_applic = product['tech_applic_en'] if product['tech_applic_en'] else ''
    description = product['description_en'] if product['description_en'] else ''
    tech_descr = product['tech_descr_en'] if product['tech_descr_en'] else ''
    
    # Combine all relevant text fields for analysis
    combined_text = f"""
Product Name: {product_name}

Technical Application: {tech_applic}

Description: {description}

Technical Description: {tech_descr}
"""
    
    # Create the extraction prompt
    extraction_prompt = f"""You are an expert in construction materials analyzing Environmental Product Declarations (EPDs).

I need you to thoroughly analyze this construction product information and extract TWO specific types of information:

PART 1: MATERIALS
List ALL specific materials that this product is physically made from. Be precise, technical, and comprehensive.
- Include exact material names (e.g., "high-density polyethylene" not just "plastic")
- Include ALL materials mentioned in the text (minimum 3 if mentioned)
- Do NOT include manufacturing tools or equipment
- Do NOT include packaging materials
- Include technical grade/type specifications if mentioned

PART 2: APPLICATIONS
List ALL specific construction applications where this product is used. Be specific and detailed.
- Include exact applications (e.g., "thermal insulation in exterior walls" not just "insulation")
- Include ALL applications mentioned in the text (minimum 3 if mentioned)
- Include specific building components where the product is used
- Include specific building types where relevant

Analyze this product information carefully:

{combined_text}

Format your answer as:

MATERIALS:
- Material 1
- Material 2
- Material 3
...

APPLICATIONS:
- Application 1
- Application 2
- Application 3
...

ONLY include these two sections with bullet points. Do not include any explanations or other text."""

    # Log the extraction prompt if requested
    if log_file:
        log_file.write(f"\n\n--- MATERIALS & USES EXTRACTION PROMPT ---\n")
        log_file.write(extraction_prompt)
    
    # Query the LLM for extraction
    extraction_response = query_llm(extraction_prompt, model)
    
    # Log the extraction response if requested
    if log_file:
        log_file.write(f"\n\n--- MATERIALS & USES EXTRACTION RESPONSE ---\n")
        log_file.write(extraction_response)
    
    # Parse the extraction response
    materials = []
    uses = []
    
    # Simple parsing of extraction response using sections
    materials_section = False
    applications_section = False
    
    for line in extraction_response.split('\n'):
        line = line.strip()
        
        if line.lower().startswith('materials:'):
            materials_section = True
            applications_section = False
            continue
        elif line.lower().startswith('applications:'):
            materials_section = False
            applications_section = True
            continue
        
        if line and line.startswith('-') and materials_section:
            material = line[1:].strip()
            if material and material not in materials:
                materials.append(material)
        
        if line and line.startswith('-') and applications_section:
            use = line[1:].strip()
            if use and use not in uses:
                uses.append(use)
    
    return {
        "materials": materials,
        "uses": uses,
        "raw_extraction": extraction_response
    }

def format_into_json(process_id, extracted_data, model, categories, log_file=None):
    """
    Second step of two-step approach: Format extracted data into proper JSON
    """
    # Create a string listing the categories
    category_text = ""
    for level in ["1", "2", "3"]:
        if categories[level]:
            for cat in categories[level]:
                classification = cat.get('classification_en', cat['classification'])
                category_text += f"- Category Level {level}: {classification}\n"
    
    # Create the formatting prompt
    formatting_prompt = f"""You are an expert in construction product data standardization.

Take the extracted materials and applications information and format it into a valid, complete JSON object.

PROCESS ID: {process_id}

EXTRACTED MATERIALS:
{', '.join(extracted_data['materials'])}

EXTRACTED APPLICATIONS:
{', '.join(extracted_data['uses'])}

PRODUCT CATEGORIES:
{category_text}

FORMAT REQUIREMENTS:
1. Use the EXACT process_id provided: "{process_id}"
2. Include a minimum of 3 materials (if available in the extracted data)
3. Include a minimum of 3 applications (if available in the extracted data)
4. Format as proper JSON with the structure shown below
5. Do not include any comments, explanations or text outside the JSON structure

JSON TEMPLATE:
{{
  "epd_uuid": "{process_id}",
  "materials": [
    "material_1",
    "material_2",
    "material_3"
  ],
  "uses": [
    "use_case_1",
    "use_case_2",
    "use_case_3"
  ]
}}

Return ONLY valid JSON. No markdown formatting, no explanations, no additional text."""

    # Log the formatting prompt if requested
    if log_file:
        log_file.write(f"\n\n--- JSON FORMATTING PROMPT ---\n")
        log_file.write(formatting_prompt)
    
    # Query the LLM for JSON formatting
    json_response = query_llm(formatting_prompt, model)
    
    # Log the JSON response if requested
    if log_file:
        log_file.write(f"\n\n--- JSON FORMATTING RESPONSE ---\n")
        log_file.write(json_response)
    
    return json_response

def validate_and_fix_json(json_str):
    """
    Attempts to validate and fix common JSON formatting issues
    """
    # Try to parse as-is first
    try:
        json_obj = json.loads(json_str)
        return json_obj, json_str
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON if model included explanations
    json_pattern = r'({[\s\S]*})'
    match = re.search(json_pattern, json_str)
    if match:
        json_candidate = match.group(0)
        try:
            json_obj = json.loads(json_candidate)
            return json_obj, json_candidate
        except json.JSONDecodeError:
            pass
    
    # More aggressive fixes: replace single quotes, fix trailing commas
    fixed_str = json_str.replace("'", '"')
    fixed_str = re.sub(r',\s*}', '}', fixed_str)
    fixed_str = re.sub(r',\s*]', ']', fixed_str)
    
    try:
        json_obj = json.loads(fixed_str)
        return json_obj, fixed_str
    except json.JSONDecodeError:
        pass
    
    # If all else fails, return None
    return None, json_str

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract product information using LLMs')
    parser.add_argument('--model', type=str, default=DEFAULT_LLM_MODEL, 
                        help=f'LLM model to use (default: {DEFAULT_LLM_MODEL})')
    parser.add_argument('--max-products', type=int, default=MAX_PRODUCTS, 
                        help=f'Maximum number of products to process (default: {MAX_PRODUCTS})')
    parser.add_argument('--skip-translation', action='store_true', 
                        help='Skip translation of German fields')
    parser.add_argument('--example-mode', action='store_true',
                        help='Include examples in prompts (may improve accuracy)')
    args = parser.parse_args()
    
    # Get selected model and create timestamp
    selected_model = args.model
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create log file for prompts and responses
    log_filename = f"product_analysis_{selected_model}_{timestamp}.log"
    print(f"Creating log file for prompts and responses: {log_filename}")
    log_file = open(log_filename, "w", encoding="utf-8")
    log_file.write(f"PRODUCT ANALYSIS LOG - Model: {selected_model}, Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load translations
    translations = load_translations()
    
    # Connect to the database
    conn = psycopg2.connect(**DB_PARAMS)
    
    try:
        # Get all products with required fields, including category levels
        cur = conn.cursor()
        cur.execute("""
            SELECT process_id, 
                   name_en, name_de,
                   description_en, description_de, 
                   tech_descr_en, tech_descr_de,
                   tech_applic_en, tech_applic_de,
                   category_level_1, category_level_2, category_level_3
            FROM products
            LIMIT %s
        """, (args.max_products,))
        products = cur.fetchall()
        cur.close()
        
        results = []
        
        # Process each product
        for i, (process_id, name_en, name_de, description_en, description_de, 
                tech_descr_en, tech_descr_de, tech_applic_en, tech_applic_de,
                category_level_1, category_level_2, category_level_3) in enumerate(products):
            product_name = name_en if name_en else name_de
            print(f"Processing product {i+1}/{len(products)}: {product_name}")
            log_file.write(f"\n\n{'='*80}\nPRODUCT {i+1}/{len(products)}: {product_name} (ID: {process_id})\n{'='*80}\n")
            
            # Create product object with all required fields and fallbacks
            product = {
                "process_id": process_id,
                "name_en": name_en,
                "name_de": name_de,
                "description_en": description_en,
                "description_de": description_de,
                "tech_descr_en": tech_descr_en,
                "tech_descr_de": tech_descr_de,
                "tech_applic_en": tech_applic_en,
                "tech_applic_de": tech_applic_de,
                "category_level_1": category_level_1,
                "category_level_2": category_level_2,
                "category_level_3": category_level_3
            }
            
            # Extract categories from product data
            categories = extract_categories_from_product(product, translations)
            
            # STEP 1: Translate German fields when English versions are missing (if not skipped)
            if not args.skip_translation:
                missing_english = any(not product[f] and product[g] for f, g in [
                    ('name_en', 'name_de'), 
                    ('description_en', 'description_de'),
                    ('tech_descr_en', 'tech_descr_de'),
                    ('tech_applic_en', 'tech_applic_de')
                ])
                
                if missing_english:
                    print(f"  > Translating missing English fields from German...")
                    log_file.write("\nTRANSLATING MISSING ENGLISH FIELDS\n")
                    product = translate_german_fields(product, selected_model, log_file)
            
            # STEP 2: Extract materials and uses (first step of two-step approach)
            print(f"  > Extracting materials and uses...")
            start_time = time.time()
            extracted_data = extract_materials_and_uses(product, selected_model, log_file)
            extraction_time = time.time() - start_time
            print(f"  > Extraction completed in {extraction_time:.2f} seconds")
            print(f"  > Found {len(extracted_data['materials'])} materials and {len(extracted_data['uses'])} uses")
            
            # STEP 3: Format into proper JSON (second step of two-step approach)
            print(f"  > Formatting into JSON...")
            start_time = time.time()
            json_response = format_into_json(process_id, extracted_data, selected_model, categories, log_file)
            formatting_time = time.time() - start_time
            print(f"  > Formatting completed in {formatting_time:.2f} seconds")
            
            # Try to parse the response as JSON
            parsed_json, clean_json = validate_and_fix_json(json_response)
            
            # Store results
            if parsed_json:
                print(f"  > Successfully parsed JSON response")
                result = {
                    "process_id": process_id,
                    "name": product_name,
                    "categories": categories,
                    "llm_analysis": parsed_json,
                    "raw_extraction": extracted_data,
                    "translations_applied": not args.skip_translation,
                    "extraction_time_seconds": extraction_time,
                    "formatting_time_seconds": formatting_time,
                    "total_time_seconds": extraction_time + formatting_time
                }
            else:
                print(f"  > Failed to parse JSON response, storing raw response")
                result = {
                    "process_id": process_id,
                    "name": product_name,
                    "categories": categories,
                    "llm_analysis": {
                        "error": "Failed to parse JSON response",
                        "raw_response": json_response
                    },
                    "raw_extraction": extracted_data,
                    "translations_applied": not args.skip_translation,
                    "extraction_time_seconds": extraction_time,
                    "formatting_time_seconds": formatting_time,
                    "total_time_seconds": extraction_time + formatting_time
                }
            
            results.append(result)
            
            # Save intermediate results after each product
            output_filename = f"products_analysis_{selected_model}_{timestamp}.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"  > Results saved to {output_filename}")
        
        # Save final results
        final_output = f"products_analysis_{selected_model}_{timestamp}_final.json"
        with open(final_output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        if not_found_translations:
            with open(f"translations_not_found_{timestamp}.txt", "w", encoding="utf-8") as f:
                for item in not_found_translations:
                    f.write(f"{item}\n")

        print(f"Analysis completed for {len(results)} products. Final results saved to {final_output}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        log_file.write(f"\n\nERROR: {str(e)}")
    finally:
        conn.close()
        log_file.close()
        print(f"Log file closed: {log_filename}")

if __name__ == "__main__":
    main()