import json
import re
from pathlib import Path
from collections import defaultdict

input_jsonl = Path("extracted_texts/text_blocks.jsonl")
output_txt = Path("extracted_texts/chunks_preview.txt")
output_json = Path("extracted_texts/chunks.json")

# Configurable parameters
max_chunk_length = 1000  # Maximum character length for a chunk
min_chunk_paragraphs = 1  # Minimum number of paragraphs per chunk
max_chunk_paragraphs = 5  # Maximum number of paragraphs per chunk

# Load extracted blocks
with open(input_jsonl, "r", encoding="utf-8") as f:
    blocks = [json.loads(line) for line in f if line.strip()]

# Group by document and page
grouped_blocks = defaultdict(list)
for block in blocks:
    grouped_blocks[(block["document"], block["page"])].append(block)

def clean_text(text):
    """Clean and normalize text"""
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    # Fix spacing around punctuation
    text = re.sub(r'\s+([.,;:!?)])', r'\1', text)
    text = re.sub(r'([([{])\s+', r'\1', text)
    return text.strip()

# For JSON output
all_chunks = []

# Process and chunk blocks
with open(output_txt, "w", encoding="utf-8") as out:
    for (doc, page), blocks in sorted(grouped_blocks.items()):
        current_section = None
        current_chunk = []
        current_chunk_text = ""
        chunk_count = 0
        
        # Clean blocks and associate with sections
        cleaned_blocks = []
        for block in blocks:
            label = block["label"]
            text = clean_text(block["text"])
            
            if not text:
                continue
                
            cleaned_blocks.append({
                "text": text,
                "label": label
            })
            
        # Process blocks in order
        for i, block in enumerate(cleaned_blocks):
            label = block["label"]
            text = block["text"]
            
            # Update section context when we encounter a title/heading
            if label in ["title", "heading"]:
                # First write out any accumulated chunk before changing section
                if current_chunk:
                    chunk_text = " ".join([b["text"] for b in current_chunk])
                    if current_section:
                        out.write(f"[{current_section}]\n")
                    else:
                        out.write("[No Section]\n")
                    out.write(chunk_text)
                    out.write("\n\n")
                    
                    # Add to JSON output
                    all_chunks.append({
                        "chunk_text": chunk_text,
                        "document": doc,
                        "page": page,
                        "section": current_section or "(No Section)"
                    })
                    
                    # Reset the chunk
                    current_chunk = []
                    current_chunk_text = ""
                    chunk_count += 1
                
                # Update the section
                current_section = text
                
                # Add the heading itself as a separate block to be chunked
                current_chunk.append(block)
                current_chunk_text += " " + text
            
            # Handle paragraph text
            elif label == "paragraph":
                # Check if adding this paragraph would exceed the chunk limits
                # We also ensure a heading stays with at least some of its content
                chunk_too_large = (
                    len(current_chunk) >= max_chunk_paragraphs or 
                    (len(current_chunk_text) + len(text) > max_chunk_length and len(current_chunk) > min_chunk_paragraphs)
                )
                
                # Don't break if the current chunk only has a heading
                heading_only = len(current_chunk) == 1 and current_chunk[0]["label"] in ["title", "heading"]
                
                if chunk_too_large and not heading_only:
                    # Write out the current chunk
                    chunk_text = " ".join([b["text"] for b in current_chunk])
                    if current_section:
                        out.write(f"[{current_section}]\n")
                    else:
                        out.write("[No Section]\n")
                    out.write(chunk_text)
                    out.write("\n\n")
                    
                    # Add to JSON output
                    all_chunks.append({
                        "chunk_text": chunk_text,
                        "document": doc,
                        "page": page,
                        "section": current_section or "(No Section)"
                    })
                    
                    # Start a new chunk with this paragraph
                    current_chunk = [block]
                    current_chunk_text = text
                    chunk_count += 1
                else:
                    # Add to the current chunk
                    current_chunk.append(block)
                    current_chunk_text += " " + text
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = " ".join([b["text"] for b in current_chunk])
            if current_section:
                out.write(f"[{current_section}]\n")
            else:
                out.write("[No Section]\n")
            out.write(chunk_text)
            out.write("\n\n")
            
            # Add to JSON output
            all_chunks.append({
                "chunk_text": chunk_text,
                "document": doc,
                "page": page,
                "section": current_section or "(No Section)"
            })

# Save JSON output
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(all_chunks, f, indent=2)

print(f"✅ Paragraph-based chunking completed:")
print(f"  - Created {len(all_chunks)} semantic chunks")
print(f"  - Text preview: {output_txt}")
print(f"  - JSON chunks: {output_json}")