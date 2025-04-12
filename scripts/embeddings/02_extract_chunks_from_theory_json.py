import json
import re
import os
import sys
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "helper_scripts")))
from llm_utils import query_llm

INPUT_FOLDER = os.path.join("data", "json_for_chunks")
OUTPUT_FILE = os.path.join("data", "chunks", "theory_chunks.json")
UNIMPORTANT_FILE = os.path.join("data", "chunks", "unimportant_chunks.json")
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
        if len(chunk.split()) > 10:
            chunks.append(chunk)
    return chunks

def is_chunk_useful(chunk):
    prompt = (
        f"The following text chunk is from a document about sustinable practices. "
        f"Does this chunk contain any theoretical or conceptual information that could help answer sustainability-related questions (e.g., about circularity, indicators like GWP, LCA methodology, materials, etc.)?\n\n"
        f"Chunk:\n{chunk}\n\n"
        f"Respond with either 'Yes, it is useful.' or 'No, it is not useful.'"
    )
    response = query_llm(prompt)
    return 'yes, it is useful' in response.lower()

def process_file(filepath):
    filename = os.path.splitext(os.path.basename(filepath))[0]
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    important_chunks = []
    unimportant_chunks = []

    all_candidate_chunks = []

    for item_index, item in enumerate(data):
        section = item.get('section', f"section_{item_index}")
        text = item.get('text', '')
        if not text.strip():
            continue

        sentences = split_into_sentences(text)
        chunks = create_chunks(sentences)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{filename}_{section}_{i}"
            metadata = {"source": "theory", "section": section}
            all_candidate_chunks.append((chunk_id, chunk, metadata))

    for chunk_id, chunk, metadata in tqdm(all_candidate_chunks, desc=f"Processing {filename}"):
        if is_chunk_useful(chunk):
            important_chunks.append({"chunk_id": chunk_id, "chunk": chunk, "metadata": metadata})
        else:
            unimportant_chunks.append({"chunk_id": chunk_id, "chunk": chunk, "metadata": metadata})

    return important_chunks, unimportant_chunks

def process_all_files():
    if not os.path.isdir(INPUT_FOLDER):
        print(f"❌ Input folder not found: {INPUT_FOLDER}")
        return [], []

    all_chunks = []
    all_unimportant = []

    for filename in os.listdir(INPUT_FOLDER):
        if filename.endswith('.json') and not filename.endswith('_chunked.json'):
            full_path = os.path.join(INPUT_FOLDER, filename)
            chunks, unimportant = process_file(full_path)
            print(f"✓ {filename}: {len(chunks)} important | {len(unimportant)} unimportant")
            all_chunks.extend(chunks)
            all_unimportant.extend(unimportant)

    return all_chunks, all_unimportant

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    chunks, unimportant = process_all_files()
    save_json(OUTPUT_FILE, chunks)
    save_json(UNIMPORTANT_FILE, unimportant)
    print(f"\n✅ Saved {len(chunks)} theory chunks to {OUTPUT_FILE}")
    print(f"🗑️ Saved {len(unimportant)} unimportant chunks to {UNIMPORTANT_FILE}")

if __name__ == "__main__":
    main()
