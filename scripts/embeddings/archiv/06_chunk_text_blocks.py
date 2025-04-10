import json
import re
from pathlib import Path
from collections import defaultdict

input_jsonl = Path("extracted_texts/text_blocks.jsonl")
output_txt = Path("extracted_texts/chunks_preview.txt")
output_json = Path("extracted_texts/chunks.json")

# Configurable parameters
max_chunk_length = 1500    # Maximum character length for a chunk
max_chunk_paragraphs = 5   # Maximum number of paragraphs per chunk
preserve_bullets = True    # Keep bullet lists together when possible

# Load extracted blocks
with open(input_jsonl, "r", encoding="utf-8") as f:
    blocks = [json.loads(line) for line in f if line.strip()]

# Group by document
doc_blocks = defaultdict(list)
for block in blocks:
    doc_blocks[block["document"]].append(block)

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
        
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    # Fix spacing around punctuation
    text = re.sub(r'\s+([.,;:!?)])', r'\1', text)
    # Fix bullet points formatting - WITHOUT using look-behind assertions
    text = re.sub(r'\n\s*▪\s*', '\n▪ ', text)  # Fix bullets after newlines
    text = re.sub(r'^\s*▪\s*', '▪ ', text)     # Fix bullets at start of string
    text = re.sub(r'\s+▪\s*', ' ▪ ', text)     # Fix bullets in middle of text
    return text.strip()

def get_section_path(block, current_section):
    """Get the section for a block"""
    if block['label'] in ['chapter', 'section']:
        return block['text']
    
    # If we have a current section, use it
    if current_section:
        return current_section
    
    return "(No Section)"

# For JSON output
all_chunks = []

# Process and chunk blocks
with open(output_txt, "w", encoding="utf-8") as out:
    for doc, blocks in doc_blocks.items():
        # Sort blocks by page
        blocks.sort(key=lambda b: b.get('page', 0))
        
        # Process blocks for chunking
        current_chunk = []
        current_section = None
        chunk_text_length = 0
        
        for i, block in enumerate(blocks):
            block_text = clean_text(block["text"])
            if not block_text:
                continue
                
            # Update current section when we encounter a heading
            if block['label'] in ['chapter', 'section']:
                current_section = block_text
                
                # Finish current chunk before starting a new section
                if current_chunk:
                    # Create chunk text
                    chunk_parts = []
                    for b in current_chunk:
                        b_text = clean_text(b['text'])
                        if not b_text:
                            continue
                        if b['label'] == 'bullet_list':
                            # Add newline before bullet list if not at start
                            if chunk_parts:
                                chunk_parts.append("\n" + b_text)
                            else:
                                chunk_parts.append(b_text)
                        else:
                            chunk_parts.append(b_text)
                    
                    chunk_text = " ".join(chunk_parts) if chunk_parts else ""
                    
                    # Write chunk
                    section_header = current_chunk[0]['label'] in ['chapter', 'section']
                    section_name = current_chunk[0]['text'] if section_header else get_section_path(current_chunk[0], current_section)
                    
                    out.write(f"[{section_name}]\n")
                    out.write(chunk_text)
                    out.write("\n\n")
                    
                    # Add to JSON output
                    all_chunks.append({
                        "chunk_text": chunk_text,
                        "document": doc,
                        "page": current_chunk[0].get('page', 1),
                        "section": section_name
                    })
                    
                    # Reset chunk
                    current_chunk = []
                    chunk_text_length = 0
                
                # Always include the heading in a chunk
                current_chunk.append(block)
                chunk_text_length += len(block_text)
                continue
            
            # Check if adding this block would exceed chunk limits
            block_will_fit = (
                len(current_chunk) < max_chunk_paragraphs or 
                (preserve_bullets and block['label'] == 'bullet_list' and 
                 current_chunk and current_chunk[-1]['label'] == 'bullet_list')
            )
            
            if block_will_fit and chunk_text_length + len(block_text) <= max_chunk_length:
                # Add to current chunk
                current_chunk.append(block)
                chunk_text_length += len(block_text)
            else:
                # Finish current chunk if it's not empty
                if current_chunk:
                    # Create chunk text
                    chunk_parts = []
                    for b in current_chunk:
                        b_text = clean_text(b['text'])
                        if not b_text:
                            continue
                        if b['label'] == 'bullet_list':
                            # Add newline before bullet list if not at start
                            if chunk_parts:
                                chunk_parts.append("\n" + b_text)
                            else:
                                chunk_parts.append(b_text)
                        else:
                            chunk_parts.append(b_text)
                    
                    chunk_text = " ".join(chunk_parts) if chunk_parts else ""
                    
                    # Write chunk
                    section_header = current_chunk[0]['label'] in ['chapter', 'section']
                    section_name = current_chunk[0]['text'] if section_header else get_section_path(current_chunk[0], current_section)
                    
                    out.write(f"[{section_name}]\n")
                    out.write(chunk_text)
                    out.write("\n\n")
                    
                    # Add to JSON output
                    all_chunks.append({
                        "chunk_text": chunk_text,
                        "document": doc,
                        "page": current_chunk[0].get('page', 1),
                        "section": section_name
                    })
                
                # Start a new chunk with this block
                current_chunk = [block]
                chunk_text_length = len(block_text)
        
        # Don't forget the last chunk
        if current_chunk:
            # Create chunk text
            chunk_parts = []
            for b in current_chunk:
                b_text = clean_text(b['text'])
                if not b_text:
                    continue
                if b['label'] == 'bullet_list':
                    # Add newline before bullet list if not at start
                    if chunk_parts:
                        chunk_parts.append("\n" + b_text)
                    else:
                        chunk_parts.append(b_text)
                else:
                    chunk_parts.append(b_text)
            
            chunk_text = " ".join(chunk_parts) if chunk_parts else ""
            
            # Write chunk
            section_header = current_chunk[0]['label'] in ['chapter', 'section']
            section_name = current_chunk[0]['text'] if section_header else get_section_path(current_chunk[0], current_section)
            
            out.write(f"[{section_name}]\n")
            out.write(chunk_text)
            out.write("\n\n")
            
            # Add to JSON output
            all_chunks.append({
                "chunk_text": chunk_text,
                "document": doc,
                "page": current_chunk[0].get('page', 1),
                "section": section_name
            })

# Fix bullet point formatting in JSON output
for chunk in all_chunks:
    chunk_text = chunk["chunk_text"]
    
    # Fix bullet point formatting without look-behind assertions
    if '▪' in chunk_text:
        # Ensure bullet points have proper spacing
        chunk_text = re.sub(r'▪(\S)', r'▪ \1', chunk_text)
        
        # Add line breaks between bullet points - using simpler pattern
        lines = chunk_text.split('\n')
        result_lines = []
        for i, line in enumerate(lines):
            result_lines.append(line)
            # If this line has a bullet and the next one does too, add a newline
            if i < len(lines) - 1 and '▪' in line and '▪' in lines[i+1]:
                result_lines.append('')  # Empty line for separation
        
        chunk_text = '\n'.join(result_lines)
    
    chunk["chunk_text"] = chunk_text

# Save JSON output
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(all_chunks, f, indent=2)

print(f"✅ Chunking completed:")
print(f"  - Created {len(all_chunks)} chunks")
print(f"  - Text preview: {output_txt}")
print(f"  - JSON chunks: {output_json}")