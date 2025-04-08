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
    }
}

# Output directories
output_dir = Path("extracted_texts")
table_dir = output_dir / "tables"
output_dir.mkdir(parents=True, exist_ok=True)
table_dir.mkdir(parents=True, exist_ok=True)

jsonl_output = output_dir / "text_blocks.jsonl"
metadata_output = output_dir / "tables_metadata.json"
table_metadata = []

def overlaps_image(x0, top, x1, bottom, image_boxes, padding=5):
    for ix0, itop, ix1, ibottom in image_boxes:
        if not (x1 < ix0 - padding or x0 > ix1 + padding or bottom < itop - padding or top > ibottom + padding):
            return True
    return False

def extract_blocks_with_context(pdf, crop_top, crop_bottom):
    """Extract text blocks with better context awareness, avoiding text inside images"""
    all_blocks = []
    
    section_pattern = re.compile(r'^\s*(\d+(\.\d+)*)\s+(.*?)\s*$')
    bullet_pattern = re.compile(r'^\s*[▪•■◆◇○●\-*]\s+')
    subsection_pattern = re.compile(r'^([A-Z][a-zA-Z\s]{2,20}):$')
    
    for page_num, page in enumerate(pdf.pages):
        width, height = page.width, page.height
        cropped = page.within_bbox((0, height * crop_top, width, height * crop_bottom))
        if not cropped:
            continue
        
        text = cropped.extract_text()
        chars = cropped.chars
        if not chars:
            continue

        image_boxes = [
            (img["x0"], img["top"], img["x1"], img["bottom"]) for img in cropped.images
        ]

        font_sizes = [char['size'] for char in chars if 'size' in char]
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 10
        
        lines = []
        line_groups = {}
        for char in chars:
            y_key = round(char['top'], 1)
            if y_key not in line_groups:
                line_groups[y_key] = []
            line_groups[y_key].append(char)

        for y_pos in sorted(line_groups.keys()):
            chars_in_line = sorted(line_groups[y_pos], key=lambda c: c['x0'])
            if not chars_in_line:
                continue
            
            x0 = min(c['x0'] for c in chars_in_line)
            x1 = max(c['x1'] for c in chars_in_line)
            top = min(c['top'] for c in chars_in_line)
            bottom = max(c['bottom'] for c in chars_in_line)

            if overlaps_image(x0, top, x1, bottom, image_boxes):
                continue  # Skip line inside image

            line_text = ''.join(c['text'] for c in chars_in_line).strip()
            if not line_text:
                continue

            line_font_sizes = [c['size'] for c in chars_in_line if 'size' in c]
            line_font_size = sum(line_font_sizes) / len(line_font_sizes) if line_font_sizes else avg_font_size
            bold_chars = sum(1 for c in chars_in_line if 'Bold' in c.get('fontname', '').split('-')[-1])
            is_bold = bold_chars > len(chars_in_line) * 0.5
            left_margin = min(c['x0'] for c in chars_in_line)

            lines.append({
                'text': line_text,
                'font_size': line_font_size,
                'is_bold': is_bold,
                'left_margin': left_margin,
                'y_pos': y_pos,
                'chars': chars_in_line
            })

        blocks = []
        current_text = ""
        current_label = ""
        current_level = 0
        active_section = None
        i = 0

        while i < len(lines):
            line = lines[i]
            text = line['text'].strip()
            if not text:
                i += 1
                continue

            section_match = section_pattern.match(text)
            if section_match:
                if current_text:
                    blocks.append({
                        'text': current_text,
                        'label': current_label,
                        'level': current_level,
                        'page': page_num + 1
                    })
                    current_text = ""

                section_num = section_match.group(1)
                section_title = section_match.group(3)
                level = len(section_num.split('.'))

                blocks.append({
                    'text': text,
                    'label': 'chapter' if level == 1 else 'section',
                    'level': level,
                    'page': page_num + 1
                })

                active_section = {
                    'text': text,
                    'level': level
                }

                i += 1

            elif bullet_pattern.match(text):
                if current_text:
                    blocks.append({
                        'text': current_text,
                        'label': current_label,
                        'level': current_level,
                        'page': page_num + 1
                    })
                    current_text = ""

                bullet_text = text
                i += 1
                while i < len(lines) and bullet_pattern.match(lines[i]['text'].strip()):
                    bullet_text += "\n" + lines[i]['text'].strip()
                    i += 1

                level = active_section['level'] + 1 if active_section else 1
                blocks.append({
                    'text': bullet_text,
                    'label': 'bullet_list',
                    'level': level,
                    'page': page_num + 1
                })

            elif subsection_pattern.match(text) and line['is_bold']:
                if current_text:
                    blocks.append({
                        'text': current_text,
                        'label': current_label,
                        'level': current_level,
                        'page': page_num + 1
                    })
                    current_text = ""

                level = active_section['level'] + 1 if active_section else 2
                blocks.append({
                    'text': text,
                    'label': 'subsection',
                    'level': level,
                    'page': page_num + 1
                })

                i += 1

            elif line['font_size'] > avg_font_size * 1.2:
                if current_text:
                    blocks.append({
                        'text': current_text,
                        'label': current_label,
                        'level': current_level,
                        'page': page_num + 1
                    })
                    current_text = ""

                level = 1 if line['font_size'] > avg_font_size * 1.3 else 2
                blocks.append({
                    'text': text,
                    'label': 'chapter' if level == 1 else 'section',
                    'level': level,
                    'page': page_num + 1
                })

                active_section = {
                    'text': text,
                    'level': level
                }

                i += 1

            else:
                if current_text:
                    ends_with_sentence = bool(re.search(r'[.!?:]$', current_text))
                    same_indentation = abs(line['left_margin'] - lines[i - 1]['left_margin']) < 15

                    if not ends_with_sentence and same_indentation:
                        current_text += " " + text
                    else:
                        blocks.append({
                            'text': current_text,
                            'label': current_label,
                            'level': current_level,
                            'page': page_num + 1
                        })
                        current_text = text
                        current_label = 'paragraph'
                        current_level = active_section['level'] + 1 if active_section else 1
                else:
                    current_text = text
                    current_label = 'paragraph'
                    current_level = active_section['level'] + 1 if active_section else 1

                i += 1

        if current_text:
            blocks.append({
                'text': current_text,
                'label': current_label,
                'level': current_level,
                'page': page_num + 1
            })

        blocks = [b for b in blocks if b['text']]
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
            blocks = extract_blocks_with_context(pdf, crop_top, crop_bottom)
            for block in blocks:
                jsonl_file.write(json.dumps({
                    "type": "text",
                    "document": pdf_path.name,
                    "page": block['page'],
                    "text": block['text'],
                    "label": block['label'],
                    "level": block['level'],
                    "crop_top": crop_top,
                    "crop_bottom": crop_bottom
                }) + "\n")

            for page_num, page in enumerate(pdf.pages):
                width, height = page.width, page.height
                cropped = page.within_bbox((0, height * crop_top, width, height * crop_bottom))

                tables = cropped.extract_tables() if cropped else []
                for table_index, table in enumerate(tables):
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

with open(metadata_output, 'w', encoding='utf-8') as f:
    json.dump(table_metadata, f, indent=2)

print(f"✅ Enhanced document extraction complete.\n- Text blocks saved to: {jsonl_output}\n- Tables saved to: {table_dir}\n- Table metadata: {metadata_output}")
