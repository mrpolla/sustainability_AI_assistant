import os

def search_word_in_xml(root_folder, word):
    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.lower().endswith(".xml"):
                file_path = os.path.join(dirpath, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if word in content.lower():
                            print(f"Found in: {file_path}")
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

# Example usage
search_word_in_xml("/home/murilo-dsr/Desktop/downloads", "78bfe151-3cf3-46cb-a1a5-61a79bbd5476")
# search_fired_brick_in_xml(os.path.join(os.getcwd(), "downloads"))
# search_fired_brick_in_xml(os.path.join(os.getcwd(), "downloads/b822aa09-3cb6-49a3-98f6-a3ebf325a70b_dependencies"))