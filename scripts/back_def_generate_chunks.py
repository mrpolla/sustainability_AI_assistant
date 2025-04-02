def generate_chunks():
    metadata = fetch_product_metadata()
    exchanges = fetch_exchanges()
    lcia = fetch_lcia()
    compliances = fetch_compliances()
    reviews = fetch_reviews()

    chunks = {}
    all_product_info = {}  # New dictionary to store concatenated information

    for pid in metadata:
        m = metadata[pid]

        shared_header = f"Product: {m['name']} ({m['uuid']})\n"

        # semantic sections
        semantic_sections = [
            ("basic_info", f"Product: {m['name']}\nYear: {m['year']}\nDescription: {m['desc']}\nClassifications: {', '.join(m['classifications'])}"),
            ("technical", f"Geo: {m['geo']} - {m['geo_descr']}\nTechnical Description: {m['tech_descr']}\nTechnical Application: {m['tech_applic']}\nTime Representation: {m['time_repr']}"),
            ("usage", f"Use Advice (EN): {m['use_advice_en']}\nUse Advice (DE): {m['use_advice_de']}"),
            ("meta", f"Generator (EN): {m['generator_en']}\nGenerator (DE): {m['generator_de']}\nEntry By (EN): {m['entry_by_en']}\nEntry By (DE): {m['entry_by_de']}\nAdmin Version: {m['admin_version']}\nLicense Type: {m['license_type']}\nAccess (EN): {m['access_en']}\nAccess (DE): {m['access_de']}\nTimestamp: {m['timestamp']}\nFormats: {m['formats']}"),
            ("compliances", "\n".join(compliances.get(pid, []))),
            ("reviews", "\n".join(reviews.get(pid, []))),
        ]
        for section, text in semantic_sections:
            sub_chunks = split_text_to_chunks(text, CHUNK_CHAR_LIMIT - len(shared_header))
            for i, chunk in enumerate(sub_chunks):
                # # Write chunks to a text file for debugging
                # with open("chunks_output.txt", "a", encoding="utf-8") as f:
                #     for chunk_id, item in chunks.items():
                #         f.write(f"Chunk ID: {chunk_id}\n")
                #         f.write(f"Process ID: {item['process_id']}\n")
                #         f.write(f"Chunk Content:\n{item['chunk']}\n")
                #         f.write("=" * 80 + "\n")  # Separator for readability

                chunk_id = f"{pid}_{section}_{i}"
                chunks[chunk_id] = {
                    "process_id": pid,
                    "chunk": shared_header + chunk
                }

        # structural sections
        structural_sections = [
            ("exchanges", "\n".join(exchanges.get(pid, []))),
            ("lcia", "\n".join(lcia.get(pid, []))),
        ]
        for section, text in structural_sections:
            sub_chunks = split_text_to_chunks(text, CHUNK_CHAR_LIMIT - len(shared_header))
            for i, chunk in enumerate(sub_chunks):
                # # Write chunks to a text file for debugging
                # with open("chunks_output.txt", "a", encoding="utf-8") as f:
                #     for chunk_id, item in chunks.items():
                #         f.write(f"Chunk ID: {chunk_id}\n")
                #         f.write(f"Process ID: {item['process_id']}\n")
                #         f.write(f"Chunk Content:\n{item['chunk']}\n")
                #         f.write("=" * 80 + "\n")  # Separator for readability

                chunk_id = f"{pid}_{section}_{i}"
                chunks[chunk_id] = {
                    "process_id": pid,
                    "chunk": shared_header + chunk
                }

        # Concatenate all sections for the product just for debug
        all_sections_text = shared_header
        for section, text in semantic_sections:
            all_sections_text += f"\n\n--- {section.upper()} ---\n{text}"

        for section, text in structural_sections:
            all_sections_text += f"\n\n--- {section.upper()} ---\n{text}"
        all_product_info[pid] = all_sections_text

    return chunks