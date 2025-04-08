import os
import csv
from typing import Dict

def merge_translation_files(directory: str, output_file: str) -> None:
    """
    Merge translation files from a directory into a single CSV, removing duplicates.
    
    Args:
        directory (str): Path to the directory containing translation files
        output_file (str): Path to the output CSV file
    """
    # Dictionary to store unique translations
    translations: Dict[str, str] = {}
    
    # Iterate through all files in the directory
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        
        # Skip if it's a directory
        if os.path.isdir(filepath):
            continue
        
        try:
            # Read the file
            with open(filepath, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                
                # Skip header if present
                try:
                    next(csv_reader)
                except StopIteration:
                    continue
                
                # Process each row
                for row in csv_reader:
                    # Ensure the row has two elements
                    if len(row) == 2:
                        original = row[0].strip()
                        translation = row[1].strip()
                        
                        # Add unique translation, keeping first encountered
                        if original not in translations:
                            translations[original] = translation
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
    
    # Sort translations by original text
    sorted_translations = sorted(translations.items())
    
    # Write to output CSV
    with open(output_file, 'w', encoding='utf-8', newline='') as file:
        csv_writer = csv.writer(file)
        
        # Write header
        csv_writer.writerow(['classification', 'classification_english'])
        
        # Write translations
        csv_writer.writerows(sorted_translations)
    
    # Print stats
    print(f"Total unique translations: {len(translations)}")

# Specify the directory containing translation files
input_directory = './translations'
output_file = 'merged_translations.csv'

# Run the merge
merge_translation_files(input_directory, output_file)
print(f"Merged translations saved to {output_file}")