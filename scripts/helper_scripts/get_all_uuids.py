import os
import xml.etree.ElementTree as ET
import pandas as pd
import zipfile
import tempfile
from tqdm import tqdm

def parse_uuid(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    namespaces = {
        'common': 'http://lca.jrc.it/ILCD/Common'
    }
    el = root.find('.//common:UUID', namespaces)
    return el.text if el is not None else None

def extract_uuids_from_zips(directory):
    uuids = []
    zip_files = []

    for root_dir, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".zip"):
                zip_files.append(os.path.join(root_dir, file))

    for zip_path in tqdm(zip_files, desc="Processing ZIP files"):
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_ref.extractall(temp_dir)
                    processes_path = os.path.join(temp_dir, "ILCD", "processes")
                    if os.path.exists(processes_path):
                        for xml_file in os.listdir(processes_path):
                            if xml_file.endswith(".xml"):
                                xml_path = os.path.join(processes_path, xml_file)
                                try:
                                    uuid = parse_uuid(xml_path)
                                    uuids.append({"uuid": uuid})
                                except Exception as e:
                                    uuids.append({"uuid": f"Error in {xml_file}: {str(e)}"})
        except Exception as e:
            uuids.append({"uuid": f"Error opening {os.path.basename(zip_path)}: {str(e)}"})

    return pd.DataFrame(uuids)

if __name__ == "__main__":
    downloads_dir = os.path.join(os.getcwd(), "downloads")
    uuid_df = extract_uuids_from_zips(downloads_dir)

    output_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "uuids_from_all_xml.csv")

    uuid_df.to_csv(output_path, index=False)
    print(f"UUIDs saved to {output_path}")
