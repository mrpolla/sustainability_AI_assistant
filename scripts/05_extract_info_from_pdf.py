import pdfplumber
from pathlib import Path
import csv
import json
import re

# Define the input PDFs with crop settings
pdf_inputs = {
    "DGNB": {
        "path": Path("books_and_isos_reference/Books/dgnb-quality-standard-for-circularity-indices-for-buildings_check.pdf"),
        "crop_top": 0.09,
        "crop_bottom": 0.98
    },
    # Add other PDFs as needed
}

# Output directories
output_dir = Path("extracted_texts")
table_dir = output_dir / "tables"
output_dir.mkdir(parents=True, exist_ok=True)
table_dir.mkdir(parents=True, exist_ok=True)

jsonl_output = output_dir / "text_blocks.jsonl"
metadata_output = output_dir / "tables_metadata.json"
table_metadata = []

def extract_complete_blocks(pdf, crop_top, crop_bottom):
    """Extract text as complete paragraphs and headings, preserving structure"""
    all_blocks = []
    
    for page_num, page in enumerate(pdf.pages):
        width, height = page.width, page.height
        cropped = page.within_bbox((0, height * crop_top, width, height * crop_bottom))
        
        # Extract all text
        text = cropped.extract_text(x_tolerance=3, y_tolerance=3)
        if not text:
            continue
            
        # Get font information for heading detection
        chars = cropped.chars
        if not chars:
            continue
            
        # Calculate average font size
        font_sizes = [char['size'] for char in chars if 'size' in char]
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 10
        
        # Create line objects with positions and font info
        lines = []
        char_by_line = {}
        
        for char in chars:
            # Round y-position to group into lines
            y_key = round(char['top'], 1)
            if y_key not in char_by_line:
                char_by_line[y_key] = []
            char_by_line[y_key].append(char)
        
        # Process each line
        sorted_y_positions = sorted(char_by_line.keys())
        for y_pos in sorted_y_positions:
            line_chars = char_by_line[y_pos]
            sorted_chars = sorted(line_chars, key=lambda c: c['x0'])
            
            # Extract font stats
            line_font_sizes = [c['size'] for c in sorted_chars if 'size' in c]
            avg_line_font = sum(line_font_sizes) / len(line_font_sizes) if line_font_sizes else avg_font_size
            
            # Check for bold text
            has_bold = any('Bold' in c.get('fontname', '') or 'bold' in c.get('fontname', '').lower() 
                          for c in sorted_chars)
            
            # Reconstruct line text
            line_text = ''.join(c['text'] for c in sorted_chars)
            if not line_text.strip():
                continue
                
            lines.append({
                'text': line_text.strip(),
                'y': y_pos,
                'font_size': avg_line_font,
                'is_bold': has_bold,
                'page': page_num + 1
            })
        
        # Now group lines into complete paragraphs and headings
        blocks = []
        current_block = None
        
        for i, line in enumerate(lines):
            # Determine if this line is likely a heading
            is_heading = False
            
            # Heading indicators:
            # 1. Larger font size
            # 2. Bold text
            # 3. Numbering patterns at start (1.2, etc.)
            # 4. Short line (but not empty)
            # 5. Followed by empty line or smaller font
            
            if line['text'].strip():
                # Check font size compared to page average
                font_ratio = line['font_size'] / avg_font_size
                
                # Check for section numbering patterns
                has_numbering = bool(re.match(r'^\s*\d+(\.\d+)*\s+\S', line['text']))
                
                # Check word count
                word_count = len(line['text'].split())
                
                # Check if next line is empty or has smaller font
                next_line_gap = False
                if i < len(lines) - 1:
                    next_line = lines[i + 1]
                    next_font_ratio = next_line['font_size'] / avg_font_size
                    line_gap = next_line['y'] - line['y']
                    next_line_gap = line_gap > 1.5 * (next_line['font_size'] / 72 * 96)  # Approx line height
                
                # Determine if this is a heading
                is_heading = (
                    (font_ratio > 1.15 and word_count < 15) or
                    (has_numbering and word_count < 20) or
                    (line['is_bold'] and word_count < 12) or
                    (font_ratio > 1.05 and next_line_gap and word_count < 20)
                )
                
                # Special case: title followed by subtitle
                is_continuation_of_title = (
                    current_block and 
                    current_block['label'] in ('title', 'heading') and
                    font_ratio > 1.1 and 
                    not line['text'].endswith('.')
                )
                
                # Bullets and lists (often not headings)
                is_bullet_point = bool(re.match(r'^\s*[\u2022\u25aa\u25A0\u25CF\u25E6\u2043\u2219•■◦*-]\s+', line['text']))
                if is_bullet_point and not has_numbering:
                    is_heading = False
            
            # Start a new block or continue the current one
            if is_heading or is_continuation_of_title:
                label = 'title' if font_ratio > 1.25 or (is_continuation_of_title and current_block['label'] == 'title') else 'heading'
                
                # If this is a continuation of a title, append to it
                if is_continuation_of_title and current_block:
                    current_block['text'] += ' ' + line['text']
                    continue
                
                # Otherwise create a new heading block
                if current_block:
                    blocks.append(current_block)
                
                current_block = {
                    'text': line['text'],
                    'label': label,
                    'page': page_num + 1
                }
            else:
                # Regular paragraph text
                if current_block and current_block['label'] == 'paragraph':
                    # Check if this is a continuation of the same paragraph
                    # Heuristic: if previous line doesn't end with period and this isn't indented
                    prev_text = current_block['text']
                    ends_with_sentence = bool(re.search(r'[.!?:]$', prev_text))
                    
                    if not ends_with_sentence:
                        # This is a continuation of the previous paragraph
                        current_block['text'] += ' ' + line['text']
                    else:
                        # This is a new paragraph
                        blocks.append(current_block)
                        current_block = {
                            'text': line['text'],
                            'label': 'paragraph',
                            'page': page_num + 1
                        }
                else:
                    # Start a new paragraph
                    if current_block:
                        blocks.append(current_block)
                    
                    current_block = {
                        'text': line['text'],
                        'label': 'paragraph',
                        'page': page_num + 1
                    }
        
        # Don't forget the last block
        if current_block:
            blocks.append(current_block)
        
        all_blocks.extend(blocks)
    
    return all_blocks

with open(jsonl_output, 'w', encoding='utf-8') as jsonl_file:
    for doc_key, config in pdf_inputs.items():
        pdf_path = config["path"]
        crop_top = config["crop_top"]
        crop_bottom = config["crop_bottom"]

        if not pdf_path.exists():
            print(f"❌ File not found: {pdf_path}")
            continue

        with pdfplumber.open(pdf_path) as pdf:
            # Extract complete paragraphs and headings
            blocks = extract_complete_blocks(pdf, crop_top, crop_bottom)
            
            # Write blocks to JSONL
            for block in blocks:
                jsonl_file.write(json.dumps({
                    "type": "text",
                    "document": pdf_path.name,
                    "page": block['page'],
                    "text": block['text'],
                    "label": block['label'],
                    "crop_top": crop_top,
                    "crop_bottom": crop_bottom
                }) + "\n")
            
            # Extract tables
            for page_num, page in enumerate(pdf.pages):
                width, height = page.width, page.height
                cropped = page.within_bbox((0, height * crop_top, width, height * crop_bottom))
                
                tables = cropped.extract_tables()
                for table_index, table in enumerate(tables):
                    # Filter out empty or invalid tables
                    if not table or not any(any(cell for cell in row if cell) for row in table):
                        continue
                        
                    table_filename = f"{pdf_path.stem}_table_pg{page_num+1}_{table_index+1}.csv"
                    table_path = table_dir / table_filename

                    with open(table_path, 'w', encoding='utf-8', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        for row in table:
                            writer.writerow([cell if cell else "" for cell in row])

                    table_metadata.append({
                        "type": "table",
                        "document": pdf_path.name,
                        "page": page_num + 1,
                        "csv_path": str(table_path),
                        "crop_top": crop_top,
                        "crop_bottom": crop_bottom
                    })

# Save table metadata
with open(metadata_output, 'w', encoding='utf-8') as f:
    json.dump(table_metadata, f, indent=2)

print(f"✅ Enhanced paragraph extraction complete.\n- Text blocks saved to: {jsonl_output}\n- Tables saved to: {table_dir}\n- Table metadata: {metadata_output}")