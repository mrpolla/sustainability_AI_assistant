import os
import json
import psycopg2
import argparse
from datetime import datetime

# === Load DB credentials from environment ===
DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

# === Default JSON file path (can be overridden via command line) ===
DEFAULT_JSON_FILE = os.path.join("data", "ai_translations", "ai_translations.json")

def insert_translations(json_file, dry_run=False):
    """
    Insert translations from the JSON file into the database.
    If dry_run is True, it will only print the operations without executing them.
    """
    # Load translation data
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Counters for statistics
    stats = {
        "products": 0,
        "lcia_results": 0,
        "exchanges": 0,
        "flow_properties": 0
    }
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # Process products translations
        for product in data.get("products", []):
            process_id = product.get("process_id")
            translations = product.get("translations", {})
            
            if translations and process_id:
                update_parts = []
                update_values = []
                
                for field, value in translations.items():
                    update_parts.append(f"{field} = %s")
                    update_values.append(value)
                
                if update_parts:
                    update_sql = f"UPDATE products SET {', '.join(update_parts)} WHERE process_id = %s"
                    update_values.append(process_id)
                    
                    if dry_run:
                        print(f"Would execute: {update_sql} with values: {update_values}")
                    else:
                        cur.execute(update_sql, update_values)
                        stats["products"] += 1
        
        # Process LCIA results translations
        for lcia in data.get("lcia_results", []):
            lcia_id = lcia.get("lcia_id")
            translation = lcia.get("translation", {})
            
            if translation and lcia_id:
                method_en_ai = translation.get("method_en_ai")
                
                if method_en_ai:
                    if dry_run:
                        print(f"Would update LCIA result {lcia_id} with method_en_ai = {method_en_ai}")
                    else:
                        cur.execute(
                            "UPDATE lcia_results SET method_en_ai = %s WHERE lcia_id = %s",
                            (method_en_ai, lcia_id)
                        )
                        stats["lcia_results"] += 1
        
        # Process exchanges translations
        for exchange in data.get("exchanges", []):
            exchange_id = exchange.get("exchange_id")
            translation = exchange.get("translation", {})
            
            if translation and exchange_id:
                flow_en_ai = translation.get("flow_en_ai")
                
                if flow_en_ai:
                    if dry_run:
                        print(f"Would update exchange {exchange_id} with flow_en_ai = {flow_en_ai}")
                    else:
                        cur.execute(
                            "UPDATE exchanges SET flow_en_ai = %s WHERE exchange_id = %s",
                            (flow_en_ai, exchange_id)
                        )
                        stats["exchanges"] += 1
        
        # Process flow properties translations
        for flow_prop in data.get("flow_properties", []):
            flow_property_id = flow_prop.get("flow_property_id")
            translation = flow_prop.get("translation", {})
            
            if translation and flow_property_id:
                name_en_ai = translation.get("name_en_ai")
                
                if name_en_ai:
                    if dry_run:
                        print(f"Would update flow property {flow_property_id} with name_en_ai = {name_en_ai}")
                    else:
                        cur.execute(
                            "UPDATE flow_properties SET name_en_ai = %s WHERE flow_property_id = %s",
                            (name_en_ai, flow_property_id)
                        )
                        stats["flow_properties"] += 1
        
        # Commit changes if not in dry run mode
        if not dry_run:
            conn.commit()
            print(f"✅ Translation data inserted successfully:")
            print(f"   - Products: {stats['products']} updated")
            print(f"   - LCIA Results: {stats['lcia_results']} updated")
            print(f"   - Exchanges: {stats['exchanges']} updated")
            print(f"   - Flow Properties: {stats['flow_properties']} updated")
        else:
            print("✅ Dry run completed. No changes were made to the database.")
    
    except Exception as e:
        print(f"❌ Error inserting translation data: {e}")
        if not dry_run and conn:
            conn.rollback()
    
    finally:
        if conn:
            cur.close()
            conn.close()
    
    return stats

def main():
    parser = argparse.ArgumentParser(description='Insert translation data into the database')
    parser.add_argument('--json-file', type=str, default=DEFAULT_JSON_FILE,
                        help=f'Path to the JSON file containing translations (default: {DEFAULT_JSON_FILE})')
    parser.add_argument('--dry-run', action='store_true',
                        help='Perform a dry run without modifying the database')
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.json_file):
        print(f"❌ Error: File not found: {args.json_file}")
        return
    
    print(f"{'DRY RUN: ' if args.dry_run else ''}Inserting translations from {args.json_file}")
    
    # Create a log with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logs_dir = os.path.join("logs", "insert_translations")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Run the insertion
    stats = insert_translations(args.json_file, args.dry_run)
    
    # Save summary to log file
    if not args.dry_run:
        summary = {
            "timestamp": datetime.now().isoformat(),
            "json_file": args.json_file,
            "stats": stats
        }
        
        log_file = os.path.join(logs_dir, f"insert_translations_{timestamp}.json")
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"Summary saved to: {log_file}")

if __name__ == "__main__":
    main()