#!/usr/bin/env python3
import json
import re
import os


def split_into_sentences(text):
    """
    Split text into sentences, handling ISO standard format
    
    Args:
        text (str): The text to split into sentences
        
    Returns:
        list: Array of sentences
    """
    if not text or text.strip() == '':
        return []
    
    # Replace section numbers and subheadings
    text = re.sub(r'^\d+(\.\d+)*\s*', '', text)
    
    # Handle period followed by newline as sentence delimiter
    text = text.replace('.\n', '.[SENTENCEBREAK]')
    
    # Handle lines starting with "Note" as separate sentences
    text = re.sub(r'\nNote \d+ to entry:', '[SENTENCEBREAK]Note to entry:', text)
    
    # Handle paragraph breaks (multiple newlines) as sentence breaks
    text = re.sub(r'\n\n+', '[SENTENCEBREAK]', text)
    
    # Replace single newlines with spaces
    text = text.replace('\n', ' ')
    
    # Split by common sentence delimiters
    sentences = re.split(r'\.(?=\s|$)|\?(?=\s|$)|\!(?=\s|$)|(?:\[SENTENCEBREAK\])', text)
    
    # Clean up the sentences
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences


def create_chunks(sentences, max_sentences_per_chunk=3):
    """
    Create chunks of sentences with specified maximum size
    
    Args:
        sentences (list): Array of sentences to chunk
        max_sentences_per_chunk (int): Maximum number of sentences per chunk
        
    Returns:
        list: Array of text chunks
    """
    if not sentences:
        return []
    
    chunks = []
    
    for i in range(0, len(sentences), max_sentences_per_chunk):
        chunk_sentences = sentences[i:i + max_sentences_per_chunk]
        chunk_text = '. '.join(chunk_sentences)
        
        # Add period if the last sentence doesn't end with a period
        chunk = chunk_text if chunk_text.endswith('.') else chunk_text + '.'
        chunks.append(chunk)
    
    return chunks


def process_json_file(input_file, max_sentences_per_chunk=3):
    """
    Process a JSON file to create chunked output
    
    Args:
        input_file (str): Path to the input JSON file
        max_sentences_per_chunk (int): Maximum number of sentences per chunk
        
    Returns:
        dict: Result of the processing
    """
    try:
        # Read and parse the input file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Array to store chunked output
        chunked_data = []
        
        # Process each item in the JSON array
        for item in data:
            section = item.get('section', '')
            text = item.get('text', '')
            
            # Skip empty text
            if not text or text.strip() == '':
                continue
            
            # Split text into sentences
            sentences = split_into_sentences(text)
            
            # Create chunks from sentences
            chunks = create_chunks(sentences, max_sentences_per_chunk)
            
            # Add each chunk to the output with the section metadata
            for chunk in chunks:
                chunked_data.append({
                    'section': section,
                    'chunk': chunk
                })
        
        # Generate output filename
        base_filename = os.path.splitext(input_file)[0]
        output_filename = f"{base_filename}_chunked.json"
        
        # Write to the output file
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(chunked_data, f, indent=2, ensure_ascii=False)
        
        return {
            'success': True,
            'input_file': input_file,
            'output_filename': output_filename,
            'total_items': len(data),
            'total_chunks': len(chunked_data)
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'input_file': input_file
        }


def process_folder(folder_path, max_sentences_per_chunk=3):
    """
    Process all JSON files in a folder
    
    Args:
        folder_path (str): Path to the folder containing JSON files
        max_sentences_per_chunk (int): Maximum number of sentences per chunk
        
    Returns:
        dict: Summary of the processing results
    """
    if not os.path.isdir(folder_path):
        return {
            'success': False,
            'error': f"Folder not found: {folder_path}"
        }
    
    # Get all JSON files in the folder
    json_files = [f for f in os.listdir(folder_path) if f.endswith('.json') and not f.endswith('_chunked.json')]
    
    if not json_files:
        return {
            'success': False,
            'error': f"No JSON files found in folder: {folder_path}"
        }
    
    results = {
        'success': True,
        'folder_path': folder_path,
        'total_files': len(json_files),
        'processed_files': 0,
        'failed_files': 0,
        'total_items': 0,
        'total_chunks': 0,
        'file_results': []
    }
    
    # Process each JSON file
    for file_name in json_files:
        file_path = os.path.join(folder_path, file_name)
        result = process_json_file(file_path, max_sentences_per_chunk)
        
        results['file_results'].append(result)
        
        if result['success']:
            results['processed_files'] += 1
            results['total_items'] += result['total_items']
            results['total_chunks'] += result['total_chunks']
        else:
            results['failed_files'] += 1
    
    return results


def main():
    """Main function - Entry point of the script"""
    # Set default max sentences per chunk
    max_sentences_per_chunk = 3
    
    folder_path = os.path.join(os.getcwd(), "data/json_for_chunks")
    print(f"Using default folder path: {folder_path}")
    
    print(f"Processing JSON files in folder: {folder_path} with max {max_sentences_per_chunk} sentences per chunk...")
    
    # Process all JSON files in the folder
    results = process_folder(folder_path, max_sentences_per_chunk)
    
    if results['success']:
        print(f"\n✅ Processing Summary:")
        print(f"Folder: {results['folder_path']}")
        print(f"Total files: {results['total_files']}")
        print(f"Successfully processed files: {results['processed_files']}")
        print(f"Failed files: {results['failed_files']}")
        print(f"Total items processed: {results['total_items']}")
        print(f"Total chunks created: {results['total_chunks']}")
        
        # Print details for each file
        print("\nFile details:")
        for result in results['file_results']:
            if result['success']:
                print(f"  ✓ {os.path.basename(result['input_file'])} → {os.path.basename(result['output_filename'])}")
                print(f"    {result['total_items']} items → {result['total_chunks']} chunks")
            else:
                print(f"  ✗ {os.path.basename(result['input_file'])}: {result['error']}")
    else:
        print(f"❌ Error: {results['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()