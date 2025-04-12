import os

def split_by_toc_marker(input_file, output_dir, marker="*****START_TABLEOFCONTENTS*****"):

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        print(f"Warning: UTF-8 decoding failed for {file_path}. Retrying with latin-1.")
        with open(file_path, 'r', encoding='latin-1') as f:
            lines = f.readlines()

    os.makedirs(output_dir, exist_ok=True)

    parts = []
    current_part = []

    for line in lines:
        if marker in line:
            if current_part:
                parts.append(current_part)
                current_part = []
            current_part.append(line)  # Keep the marker in the start of each part
        else:
            current_part.append(line)

    # Add the last part
    if current_part:
        parts.append(current_part)

    # Write each part to a new file
    for i, part in enumerate(parts, start=1):
        out_path = os.path.join(output_dir, f"split_part_{i}.txt")
        with open(out_path, 'w', encoding='utf-8') as out_f:
            out_f.writelines(part)
        print(f"✅ Wrote: {out_path}")

if __name__ == "__main__":

    filename = "Sustainable_Construction.txt"
    folder_path = os.path.join(os.getcwd(), "data/books_and_isos_reference/converted")
    output_folder = os.path.join(folder_path, "extracted_sections")
    file_path = os.path.join(folder_path, filename)
    split_by_toc_marker(file_path, os.path.join(folder_path,"output"))