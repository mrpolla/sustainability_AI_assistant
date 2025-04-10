import os
import re
import sys
import json

def extract_sections_from_file(file_path, output_folder=None):
    """
    Extract sections from a text file based on its table of contents.
    
    Args:
        file_path (str): Path to the text file
        output_folder (str, optional): Folder to save extracted sections
        
    Returns:
        tuple or None: (section_titles, section_content) if TOC found, None otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f"Warning: UTF-8 decoding failed for {file_path}. Retrying with latin-1.")
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()
                
    # Look for table of contents with expanded patterns
    # This pattern looks for "Table of Contents", "Contents", or "Contents Page" as headers
    toc_patterns = [
        re.compile(r'(?:Table\s+of\s+Contents|Contents)(?:\s*\n|$)', re.IGNORECASE),
        re.compile(r'Contents\s+Page', re.IGNORECASE)
    ]
    
    toc_start = None
    for pattern in toc_patterns:
        toc_match = pattern.search(content)
        if toc_match:
            toc_start = toc_match.start()
            break
    
    if toc_start is None:
        print(f"Table of contents not found in {file_path}")
        return None
    
    # Find the start of the TOC
    # Split content after TOC header into lines
    remaining_content = content[toc_start:]
    lines = remaining_content.split('\n')
    
    # Skip the TOC header line(s)
    i = 0
    while i < len(lines) and (re.match(r'^\s*(?:Table\s+of\s+Contents|Contents)\s*$', lines[i], re.IGNORECASE) or 
                              re.match(r'^\s*Contents\s+Page\s*$', lines[i], re.IGNORECASE)):
        i += 1
    
    # Now find the end of the TOC
    toc_lines = []
    in_toc = False
    toc_end_line = 0
    
    # Enhanced section patterns for different TOC formats
    section_patterns = [
        # Standard numbered sections with page numbers: "1. Section Title 5"
        re.compile(r'^\s*(?:\d+(?:\.\d+)*)\s+[\w\s\-&:,\(\)\'\"\/]+\s+\d+\s*$'),
        # Lettered sections with page numbers: "A. Section Title 5"
        re.compile(r'^\s*(?:[A-Z](?:\.\d+)*)\s+[\w\s\-&:,\(\)\'\"\/]+\s+\d+\s*$'),
        # Section titles with page numbers: "Foreword iv" or "Introduction v"
        re.compile(r'^\s*([\w\s\-&:,\(\)\'\"\/]+)\s+(?:[ivxlcdm]+|\d+)\s*$', re.IGNORECASE),
        # Numbered subsections with page numbers: "4.1 Units 4"
        re.compile(r'^\s*\d+\.\d+(?:\.\d+)*\s+[\w\s\-&:,\(\)\'\"\/]+\s+\d+\s*$'),
        # Pattern for EXECUTIVE SUMMARY type headers with page numbers
        re.compile(r'^\s*(?:[A-Z\s]+)\s+\d+\s*$'),
        # Pattern for "Annex A (informative) Title 22" format
        re.compile(r'^\s*Annex\s+[A-Z]\s+\([a-z]+\)\s+[\w\s\-&:,\(\)\'\"\/]+\s+\d+\s*$', re.IGNORECASE),
        # Pattern for Bibliography with page number
        re.compile(r'^\s*Bibliography\s+\d+\s*$', re.IGNORECASE),
        # Pattern for Index with page number
        re.compile(r'^\s*Index\s+\d+\s*$', re.IGNORECASE)
    ]
    
    for j in range(i, len(lines)):
        line = lines[j].strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Check if this line matches any section pattern
        is_section_line = any(pattern.match(line) for pattern in section_patterns)
        
        if is_section_line:
            in_toc = True
            toc_lines.append(line)
        elif in_toc:
            # If we've been in TOC and found a non-matching line, check if it looks like content
            # First, look for common section headings that might indicate start of content
            if re.match(r'^\s*(?:\d+(?:\.\d+)*\s+)?(?:Introduction|Overview|Scope|Foreword)\s*$', line, re.IGNORECASE):
                toc_end_line = j
                break
            
            # If we encounter copyright notices or similar text, it's likely the end of the TOC
            if re.search(r'(?:copyright|©|\(c\)|All rights reserved)', line, re.IGNORECASE):
                toc_end_line = j
                break
                
            # If we've collected several TOC entries and find a line that doesn't match the pattern
            # and has no page number, it might be the end of TOC
            if len(toc_lines) > 3 and not re.search(r'\d+\s*$', line) and not re.search(r'[ivxlcdm]+\s*$', line, re.IGNORECASE):
                toc_end_line = j
                break
    
    # If we didn't find a clear end, assume TOC goes until we've found at least 5 consecutive
    # non-TOC-like lines (to handle multi-column TOCs)
    if toc_end_line == 0 and len(toc_lines) > 0:
        non_toc_count = 0
        for j in range(i + len(toc_lines), min(i + len(toc_lines) + 50, len(lines))):
            line = lines[j].strip()
            if not line:
                continue
                
            is_section_line = any(pattern.match(line) for pattern in section_patterns)
            if not is_section_line:
                non_toc_count += 1
            else:
                non_toc_count = 0
                
            if non_toc_count >= 5:
                toc_end_line = j - non_toc_count + 1
                break
    
    # If we still didn't find the end, use a reasonable guess based on collected TOC lines
    if toc_end_line == 0 and len(toc_lines) > 0:
        toc_end_line = i + len(toc_lines) + 5  # Add a small buffer
    
    # Extract the TOC text
    toc_text = '\n'.join(lines[i:toc_end_line])
    
    # Process the TOC to extract section titles
    section_titles = []
    
    for line in toc_text.split('\n'):
        line = line.strip()
        if not line or re.match(r'^\s*(?:Table\s+of\s+Contents|Contents|Contents\s+Page)\s*$', line, re.IGNORECASE):
            continue
        
        # Remove page numbers - page numbers are typically digits or Roman numerals at the end of the line
        # but preserve section numbers at the beginning
        section_line = re.sub(r'\s+(?:\d+|[ivxlcdm]+)\s*$', '', line, flags=re.IGNORECASE)
        
        # Extract section number and title
        section_match = re.match(r'^(\s*(?:\d+(?:\.\d+)*|[A-Z](?:\.\d+)*)\s+)?([\w\s\-&:,\(\)\'\"\/]+)$', section_line)
        
        # Handle "Annex A (informative) Title" format
        annex_match = re.match(r'^(Annex\s+[A-Z]\s+\([a-z]+\)\s+)([\w\s\-&:,\(\)\'\"\/]+)$', section_line, re.IGNORECASE)
        
        if section_match:
            number = section_match.group(1).strip() if section_match.group(1) else ""
            title = section_match.group(2).strip()
            full_title = f"{number} {title}" if number else title
            section_titles.append(full_title)
        elif annex_match:
            prefix = annex_match.group(1).strip()
            title = annex_match.group(2).strip()
            full_title = f"{prefix} {title}"
            section_titles.append(full_title)
        else:
            # For special sections like "Bibliography" or "Index"
            special_section_match = re.match(r'^(Bibliography|Index|Foreword|Introduction)$', section_line, re.IGNORECASE)
            if special_section_match:
                section_titles.append(special_section_match.group(1).strip())
            # For all-caps sections like "EXECUTIVE SUMMARY"
            elif re.match(r'^([A-Z\s]+)$', section_line):
                section_titles.append(section_line.strip())
    
    # Now find where each section begins and ends in the actual content
    section_content = {}
    
    # Find start of main content (after TOC)
    content_start_pos = toc_start
    content_text = content[content_start_pos:]
    
    # Directly extract sections using regex for numbered sections
    # This approach is more reliable for standard document formats
    sections = []
    section_pattern = re.compile(r'\n(\d+(?:\.\d+)*)\s+([^\n]+?)(?:\s*\t*\d+)?\r?\n')
    
    # Find all numbered sections in the document
    for match in section_pattern.finditer(content_text):
        section_number = match.group(1)
        section_title = match.group(2).strip()
        full_title = f"{section_number} {section_title}"
        start_pos = match.end()  # End of the matched section header
        
        # Check if this section title is in our TOC-extracted titles
        found_in_toc = False
        for toc_title in section_titles:
            if toc_title.startswith(section_number) and section_title in toc_title:
                sections.append({
                    'title': toc_title,
                    'start_pos': start_pos,
                    'match_start': match.start()
                })
                found_in_toc = True
                break
        
        if not found_in_toc:
            # If not found in TOC titles, use the title as is
            sections.append({
                'title': full_title,
                'start_pos': start_pos,
                'match_start': match.start()
            })
    
    # Sort sections by their position in the document
    sections.sort(key=lambda x: x['match_start'])
    
    # Extract content between sections
    for i, section in enumerate(sections):
        current_title = section['title']
        start_pos = section['start_pos']
        
        # Content ends at the next section or the end of the document
        if i < len(sections) - 1:
            end_pos = sections[i + 1]['match_start']
        else:
            end_pos = len(content_text)
        
        # Extract content between this section header and the next
        section_text = content_text[start_pos:end_pos].strip()
        section_content[current_title] = section_text
    
    # Special handling for other non-numbered sections (like Bibliography, Annex, etc.)
    for title in section_titles:
        # Skip already processed numbered sections
        if title in section_content:
            continue
        
        # Handle special sections like Annex, Bibliography, etc.
        if re.match(r'^Annex\s+[A-Z]', title, re.IGNORECASE) or title in ['Bibliography', 'Index']:
            # Create pattern for the special section
            if re.match(r'^Annex\s+[A-Z]\s+\([a-z]+\)\s+', title, re.IGNORECASE):
                annex_match = re.match(r'^(Annex\s+[A-Z])\s+\([a-z]+\)\s+([\w\s\-&:,\(\)\'\"\/]+)$', title, re.IGNORECASE)
                if annex_match:
                    annex_part = annex_match.group(1)
                    title_part = annex_match.group(2)
                    pattern = re.compile(r'\n' + re.escape(annex_part) + r'\s+\([a-z]+\)\s+' + 
                                        re.escape(title_part) + r'(?:\s*\t*\d+)?\r?\n', re.IGNORECASE)
            else:
                pattern = re.compile(r'\n' + re.escape(title) + r'(?:\s*\t*\d+)?\r?\n', re.IGNORECASE)
            
            # Find the section in the content
            match = pattern.search(content_text)
            if match:
                start_pos = match.end()
                
                # Find the end of this section (start of any section that comes after it)
                end_pos = len(content_text)
                for section in sections:
                    if section['match_start'] > match.start():
                        end_pos = section['match_start']
                        break
                
                # Extract content
                section_text = content_text[start_pos:end_pos].strip()
                section_content[title] = section_text
    
    # Add empty content for any sections still missing
    for title in section_titles:
        if title not in section_content:
            section_content[title] = ""
    
    # Save sections to files if output folder is provided
    if output_folder and section_titles and section_content:
        save_sections_to_files(file_path, section_titles, section_content, output_folder)
    
    return section_titles, section_content

def save_sections_to_files(original_file_path, section_titles, section_content, output_folder):
    """
    Save extracted sections to JSON and TXT files.
    
    Args:
        original_file_path (str): Path to the original text file
        section_titles (list): List of section titles
        section_content (dict): Dictionary with section content
        output_folder (str): Folder to save the output files
    """
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get the base name of the original file without extension
    base_name = os.path.splitext(os.path.basename(original_file_path))[0]
    
    # Create a JSON file with all sections
    json_data = []
    for title in section_titles:
        if title in section_content:  # Make sure the section has content
            json_data.append({
                "section": title,
                "text": section_content[title].strip()
            })
    
    json_file_path = os.path.join(output_folder, f"{base_name}.json")
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved all sections to {json_file_path}")
    
    # Create a single TXT file with clear section delimitation
    txt_file_path = os.path.join(output_folder, f"{base_name}_converted.txt")
    with open(txt_file_path, 'w', encoding='utf-8') as f:
        f.write(f"Document: {original_file_path}\n\n")
        for title in section_titles:
            if title in section_content:  # Make sure the section has content
                f.write(f"{'='*80}\n")
                f.write(f"SECTION: {title}\n")
                f.write(f"{'='*80}\n\n")
                f.write(section_content[title])
                f.write("\n\n")
    
    print(f"Saved all sections to single file: {txt_file_path}")

def process_folder(folder_path, output_folder=None):
    """
    Process all .txt files in the given folder to extract sections from their table of contents.
    
    Args:
        folder_path (str): Path to the folder containing .txt files
        output_folder (str, optional): Folder to save extracted sections
    
    Returns:
        dict: Dictionary with filenames as keys and their extracted sections as values
    """
    # Ensure the folder path exists
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} does not exist.")
        return {}
    
    # Create output folder if specified and doesn't exist
    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder, exist_ok=True)
    
    results = {}
    
    # Get list of all .txt files in the folder
    txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    print(f"Found {len(txt_files)} .txt files in {folder_path}")
    
    # Process each .txt file in the folder
    for file_name in txt_files:
        file_path = os.path.join(folder_path, file_name)
        print(f"\nProcessing {file_name}...")
            
        result = extract_sections_from_file(file_path, output_folder)
        if result:
            section_titles, section_content = result
            results[file_name] = {'sections': section_titles, 'content': section_content}
            
            print(f"Found {len(section_titles)} sections:")
            for title in section_titles:
                print(f"  - {title}")
            
            print("\nContent by section (sample):")
            for title, content in section_content.items():
                # Show first 100 chars of content as preview
                content_text = content.strip()
                preview = content_text[:100].replace('\n', ' ') + "..." if len(content_text) > 100 else content_text
                print(f"\n{title}:\n{preview}")
        else:
            results[file_name] = None
    
    return results

# Example usage
if __name__ == "__main__":
    # Check if an argument for the input folder is provided
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
        # Use second argument as output folder if provided, otherwise create a subfolder
        output_folder = sys.argv[2] if len(sys.argv) > 2 else os.path.join(folder_path, "extracted_sections")
    else:
        # Default paths for debugging
        folder_path = os.path.join(os.getcwd(), "data/books_and_isos_reference/converted")
        output_folder = os.path.join(folder_path, "extracted_sections")
    
    print(f"Using folder path: {folder_path}")
    print(f"Output will be saved to: {output_folder}")
    
    # Make sure the folder exists
    if not os.path.exists(folder_path):
        print(f"Error: Folder {folder_path} does not exist.")
        sys.exit(1)
    
    # Process the folder
    results = process_folder(folder_path, output_folder)
    
    # Summary of processing
    print("\n" + "="*50)
    print(f"SUMMARY: Processed {len(results)} files")
    
    files_with_toc = sum(1 for r in results.values() if r is not None)
    print(f"Files with table of contents: {files_with_toc}")
    print(f"Files without table of contents: {len(results) - files_with_toc}")
    
    if files_with_toc > 0:
        total_sections = sum(len(r['sections']) for r in results.values() if r is not None)
        avg_sections = total_sections / files_with_toc
        print(f"Average sections per file: {avg_sections:.1f}")
        
        # List files without a table of contents
        if len(results) - files_with_toc > 0:
            print("\nFiles without table of contents:")
            for filename, result in results.items():
                if result is None:
                    print(f"  - {filename}")