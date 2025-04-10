import os
import json
import sys
from tqdm import tqdm

# Adjust import path for ../helper_scripts/llm_utils.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "helper_scripts")))
from llm_utils import query_llm

INPUT_FILE = "data/chunks/theory_chunks.json"  # or theory_chunks.json
OUTPUT_FILE = INPUT_FILE.replace(".json", "_tagged.json")
MODEL_NAME = "llama3"
MAX_TAGS = 4
LIMIT = None # Limit number of chunks processed (set to None for full run)

def build_prompt(chunk_text, metadata, chunk_id):
    source = metadata.get("source", "unknown")
    section = metadata.get("section", "")
    context_lines = []

    if source == "epd":
        product_name = metadata.get("product_name", "")
        categories = [metadata.get("category_level_1", ""), metadata.get("category_level_2", ""), metadata.get("category_level_3", "")]
        categories = [c for c in categories if c]
        materials = metadata.get("materials", [])
        use_cases = metadata.get("use_cases", [])

        if product_name:
            context_lines.append(f"Product name: {product_name}")
        if categories:
            context_lines.append(f"Category: {', '.join(categories)}")
        if materials:
            context_lines.append(f"Materials: {', '.join(materials)}")
        if use_cases:
            context_lines.append(f"Use cases: {', '.join(use_cases)}")
        context_lines.append(f"Section: {section}")

        task = (
            "You are an expert in environmental product data and sustainability in construction. "
            f"Analyze the following product-related information from an Environmental Product Declaration (EPD). "
            f"Your task is to generate {MAX_TAGS} abstract, non-redundant tags that describe key sustainability features, functional roles, performance properties, environmental aspects, or applications of the product. "
            "These tags should support semantic retrieval. "
            "Avoid directly copying product names, categories, or raw materials unless semantically important. "
            "Prefer high-level, reusable concepts like 'recyclable', 'acoustic insulation', or 'interior applications'. "
            "Do not include any explanation or intro text. Only respond with the list of tags, separated by commas."
            "If no meaningful sustainability topic is present, return only: []."
        )

    elif source == "theory":
        filename = chunk_id.split("_")[0]
        context_lines.append(f"Theory document: {filename}")
        context_lines.append(f"Section: {section}")

        task = (
            "You are analyzing theoretical or regulatory content related to sustainable construction practices. "
            f"Extract {MAX_TAGS} high-level concepts or topics that capture the key ideas, frameworks, goals, or methodologies in the text. "
            "These tags should support semantic retrieval. "
            "Avoid repeating section names or generic words like 'sustainability'. "
            "Focus on domain-specific ideas such as 'life cycle assessment', 'circular economy', or 'material reuse'. "
            "Do not include any explanation or intro text. Only respond with the list of tags, separated by commas."
            "If no meaningful sustainability topic is present, return only: []."
        )

    else:
        task = f"Generate {MAX_TAGS} relevant and diverse tags for the following content."

    prompt = (
        task + "\n\n"
        + "\n".join(context_lines)
        + "\n\n"
        + f'Text:\n"""\n{chunk_text.strip()}\n"""'
    )
    return prompt

def generate_tags(text, metadata, chunk_id, model=MODEL_NAME):
    prompt = build_prompt(text, metadata, chunk_id)
    response = query_llm(prompt, model_name=model)
    return [tag.strip() for tag in response.split(",") if tag.strip()]

def tag_chunks(input_file=INPUT_FILE, output_file=OUTPUT_FILE):
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if LIMIT:
        chunks = chunks[:LIMIT]

    tagged_chunks = []
    for chunk in tqdm(chunks, desc="Tagging Chunks"):
        metadata = chunk.get("metadata", {})
        if "tags" in metadata and metadata["tags"]:
            tagged_chunks.append(chunk)
            continue

        tags = generate_tags(chunk["chunk"], metadata, chunk["chunk_id"])
        metadata["tags"] = tags
        chunk["metadata"] = metadata
        tagged_chunks.append(chunk)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(tagged_chunks, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(tagged_chunks)} tagged chunks to {output_file}")

if __name__ == "__main__":
    tag_chunks()
