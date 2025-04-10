#!/usr/bin/env python3
import json
import re
import os

INPUT_FOLDER = os.path.join("data", "json_for_chunks")
OUTPUT_FILE = os.path.join("data", "chunks", "theory_chunks.json")
MAX_SENTENCES_PER_CHUNK = 4

def split_into_sentences(text):
    if not text or text.strip() == '':
        return []

    text = re.sub(r'^\d+(\.\d+)*\s*', '', text)
    text = text.replace('.\n', '.[SENTENCEBREAK]')
    text = re.sub(r'\nNote \d+ to entry:', '[SENTENCEBREAK]Note to entry:', text)
    text = re.sub(r'\n\n+', '[SENTENCEBREAK]', text)
    text = text.replace('\n', ' ')
    sentences = re.split(r'\.(?=\s|$)|\?(?=\s|$)|\!(?=\s|$)|(?:\[SENTENCEBREAK\])', text)
    return [s.strip() for s in sentences if s.strip()]

def create_chunks(sentences, max_sentences=MAX_SENTENCES_PER_CHUNK):
    if not sentences:
        return []
    chunks = []
    for i in range(0, len(sentences), max_sentences):
        chunk_sentences = sentences[i:i + max_sentences]
        chunk_text = '. '.join(chunk_sentences)
        chunk = chunk_text if chunk_text.endswith('.') else chunk_text + '.'
        chunks.append(chunk)
    return chunks

def process_file(filepath):
    filename = os.path.splitext(os.path.basename(filepath))[0]
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chunked_data = []

    for item_index, item in enumerate(data):
        section = item.get('section', f"section_{item_index}")
        text = item.get('text', '')

        if not text or not text.strip():
            continue

        sentences = split_into_sentences(text)
        chunks = create_chunks(sentences)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{filename}_{section}_{i}"
            chunked_data.append({
                "chunk_id": chunk_id,
                "chunk": chunk,
                "metadata": {
                    "source": "theory",
                    "section": section
                }
            })

    return chunked_data

def process_all_files():
    if not os.path.isdir(INPUT_FOLDER):
        print(f"❌ Input folder not found: {INPUT_FOLDER}")
        return []

    all_chunks = []

    for filename in os.listdir(INPUT_FOLDER):
        if filename.endswith('.json') and not filename.endswith('_chunked.json'):
            full_path = os.path.join(INPUT_FOLDER, filename)
            chunks = process_file(full_path)
            print(f"✓ {filename}: {len(chunks)} chunks")
            all_chunks.extend(chunks)

    return all_chunks

def save_chunks(chunks):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved {len(chunks)} theory chunks to {OUTPUT_FILE}")

def main():
    chunks = process_all_files()
    save_chunks(chunks)

if __name__ == "__main__":
    main()
