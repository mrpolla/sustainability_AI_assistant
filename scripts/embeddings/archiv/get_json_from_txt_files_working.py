import os
import re
import json

def load_found_sections_from_txt(txt_output_path):
    found_sections = {}

    if not os.path.exists(txt_output_path):
        return found_sections

    with open(txt_output_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            match = re.match(r'^section:(.+?)\s*\|\s*line:(\d+)$', line)
            if match:
                section = match.group(1).strip()
                index = int(match.group(2))
                found_sections[section] = index

    return found_sections

def check_found_sections_from_txt(content, found_sections):
    different_sections = []
    lines = content.splitlines()
    start_line = 0
    for section in found_sections:
        start_line = found_sections[section]
        for idx, line in enumerate(lines):
            if idx < start_line:
                continue
            if section.lower() in line.lower():
                if section in line:
                    break
                else:
                    different_sections.append(section)
                    print(f"[DIFFERENT] Section '{section}' found at line {idx+1} but different from index.")
                    break

def get_section_indexes(content, sections, start_line, output_folder=None, original_filename="output"):

    # Paths for section content and index
    txt_output_path = os.path.join(output_folder, f"{original_filename}_sections.txt")

    found_sections = load_found_sections_from_txt(txt_output_path)
    # check_found_sections_from_txt(content, found_sections)

    not_found_sections = {}
    lines = content.splitlines()
    with open(txt_output_path, 'a', encoding='utf-8') as txt_out:
        for section in sections:
            if section in found_sections:
                line_id = found_sections[section]
                print(f"[SKIP] Already found: '{section}' at line {line_id}")
                start_line = line_id
                continue

            found = False
            for idx, line in enumerate(lines):
                if idx < start_line:
                    continue
                if section.lower() in line.lower():
                    found_sections[section] = idx
                    start_line = idx
                    if found:
                        txt_out.write(f"section:{section} | line:{idx} DUPLICATE!!!\n\n")
                    else:
                        found = True
                        txt_out.write(f"section:{section} | line:{idx}\n\n")
                    
                    txt_out.flush()

            # if not found:
            #     for idx, line in enumerate(lines):
            #         if idx < start_line:
            #             continue
            #         if is_fuzzy_match(section, line):
            #             found_sections[section] = idx
            #             start_line = idx
            #             if found:
            #                 txt_out.write(f"section:{section} | line:{idx} DUPLICATE!!!\n\n")
            #             else:
            #                 found = True
            #                 txt_out.write(f"section:{section} | line:{idx}\n\n")
                        
            #             txt_out.flush()


            if not found:
                txt_out.write(f"section:{section} | NOT FOUND!!\n\n")
                not_found_sections[section] = "Not found"
                print(f"[NOT FOUND] Section '{section}'")

    return found_sections

def is_fuzzy_match(section, line):
    # Split section into words
    words = section.strip().split()

    # Build regex pattern: words separated by any whitespace (space, tab, etc.)
    pattern = r"\s+".join(re.escape(word) for word in words)

    # Search in line (case-insensitive)
    return re.search(pattern, line, re.IGNORECASE) is not None


def get_sections_to_json(found_sections, content, output_folder=None, original_filename="output"):

    lines = content.splitlines()
    json_output_path = os.path.join(output_folder, f"{original_filename}_sections.json")

    # Sort sections by their line index
    sorted_sections = sorted(found_sections.items(), key=lambda x: x[1])
    result = []

    for i in range(len(sorted_sections)):
        section_title, start_idx = sorted_sections[i]
        end_idx = sorted_sections[i + 1][1] if i + 1 < len(sorted_sections) else len(lines)

        # Clean and combine lines from start to end
        section_lines = [line.strip() for line in lines[start_idx:end_idx]]
        section_text = " ".join(section_lines).strip()

        result.append({
            "section": section_title,
            "text": section_text
        })

    # Save result to JSON
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved extracted section texts to {json_output_path}")
    return result

def extract_toc_sections(content):

    sections = []
    in_toc = False
    lines = content.splitlines()

    for idx, line in enumerate(lines):
        # Skip empty lines
        if not line.strip():
            continue
        if 'START_TABLEOFCONTENTS' in line:
            in_toc = True
            continue
        elif 'END_TABLEOFCONTENTS' in line:
            start_line = idx
            in_toc = False
            continue

        if in_toc and line:
            # Remove the last part after the last tab or last space
            if '\t' in line:
                section = line.rsplit('\t', 1)[0]
            elif ' ' in line:
                section = line.rsplit(' ', 1)[0]
            else:
                section = line  # no delimiter, use full line

            section = section.strip()
            sections.append(section)

    return sections, start_line


def process_file(file_path, output_folder=None):
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist.")
        return {}

    if output_folder:
        os.makedirs(output_folder, exist_ok=True)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f"Warning: UTF-8 decoding failed for {file_path}. Retrying with latin-1.")
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()


    sections, start_line = extract_toc_sections(content)
    found_sections = get_section_indexes(content, sections, start_line, output_folder, os.path.splitext(os.path.basename(file_path))[0])
    get_sections_to_json(found_sections, content, output_folder, os.path.splitext(os.path.basename(file_path))[0])


if __name__ == "__main__":

    filename = "Guideline_for_Sustainable_Building.txt"

    folder_path = os.path.join(os.getcwd(), "data/books_and_isos_reference/converted")
    output_folder = os.path.join(folder_path, "extracted_sections")
    file_path = os.path.join(folder_path, filename)

    print(f"Using folder path: {folder_path}")
    print(f"Output will be saved to: {output_folder}")

    results = process_file(file_path, output_folder)
    print("\n" + "="*50)
