import os
import re
import json


def extract_sections_from_file(file_path, output_folder=None):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f"Warning: UTF-8 decoding failed for {file_path}. Retrying with latin-1.")
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()

    lines = content.split('\n')
    toc_start_idx = -1
    toc_keywords = ['table of contents', 'contents page', 'contents']
    for i, line in enumerate(lines):
        if any(k in line.lower() for k in toc_keywords):
            toc_start_idx = i
            break

    if toc_start_idx == -1:
        print(f"No TOC found in {file_path}")
        return _assign_all_to_single_section(content, "[no section]", output_folder, file_path)

    toc_lines = []
    for i in range(toc_start_idx + 1, min(len(lines), toc_start_idx + 100)):
        line = lines[i].strip()
        if re.search(r'\.{2,}\s*\d+$', line):
            line = re.sub(r'\.{2,}\s*\d+$', '', line).strip()
        if len(line.split()) >= 2:
            toc_lines.append(line)
        elif len(toc_lines) > 3:
            break

    section_titles = ["[no section]"] + toc_lines
    return _split_and_assign_sections(content, section_titles, output_folder, file_path)


def _assign_all_to_single_section(content, title, output_folder, file_path):
    section_content = {title: content.strip()}
    if output_folder:
        save_sections_to_files(file_path, [title], section_content, output_folder)
    return [title], section_content


def _split_and_assign_sections(content, section_titles, output_folder, file_path):
    section_content = {}
    current_section = section_titles[0]
    section_content[current_section] = []

    # Compile regexes for each section title for efficient matching
    section_patterns = {
        title: re.compile(rf"^\s*{re.escape(title)}\s*$", re.IGNORECASE) for title in section_titles[1:]
    }

    for line in content.splitlines():
        line_stripped = line.strip()
        matched_section = None

        for title, pattern in section_patterns.items():
            if pattern.match(line_stripped):
                matched_section = title
                break

        if matched_section:
            current_section = matched_section
            if current_section not in section_content:
                section_content[current_section] = []
        section_content.setdefault(current_section, []).append(line)

    # Convert line lists into joined strings
    section_content = {
        title: '\n'.join(lines).strip() for title, lines in section_content.items()
    }

    titles_order = [title for title in section_titles if title in section_content]

    if output_folder:
        save_sections_to_files(file_path, titles_order, section_content, output_folder)

    return titles_order, section_content



def save_sections_to_files(original_file_path, section_titles, section_content, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(original_file_path))[0]

    json_data = [{"section": title, "text": section_content.get(title, "").strip()} for title in section_titles]
    json_file_path = os.path.join(output_folder, f"{base_name}.json")
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    txt_file_path = os.path.join(output_folder, f"{base_name}_converted.txt")
    with open(txt_file_path, 'w', encoding='utf-8') as f:
        f.write(f"Document: {original_file_path}\n\n")
        for title in section_titles:
            f.write(f"{'='*80}\nSECTION: {title}\n{'='*80}\n\n")
            f.write(section_content.get(title, ""))
            f.write("\n\n")


def process_folder(folder_path, output_folder=None):
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} does not exist.")
        return {}

    if output_folder:
        os.makedirs(output_folder, exist_ok=True)

    txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    results = {}
    for file_name in txt_files:
        file_path = os.path.join(folder_path, file_name)
        print(f"\nProcessing {file_name}...")
        result = extract_sections_from_file(file_path, output_folder)
        results[file_name] = result
    return results


if __name__ == "__main__":
    folder_path = os.path.join(os.getcwd(), "data/books_and_isos_reference/converted")
    output_folder = os.path.join(folder_path, "extracted_sections")

    print(f"Using folder path: {folder_path}")
    print(f"Output will be saved to: {output_folder}")

    results = process_folder(folder_path, output_folder)
    print("\n" + "="*50)
    print(f"SUMMARY: Processed {len(results)} files")
    print(f"Files with TOC: {sum(1 for r in results.values() if r is not None)}")
