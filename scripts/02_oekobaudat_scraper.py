import os
import time
import zipfile
import xml.etree.ElementTree as ET
import psycopg2
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options
import tempfile
import shutil
import logging
from dotenv import load_dotenv
import re

target_indicators = set([
    "PERE", "PERM", "PERT", "PENRE", "PENRM", "PENRT", "SM", "RSF", "NRSF", "FW",
    "HWD", "NHWD", "RWD", "CRU", "MFR", "MER", "EEE", "EET",
    "GWP-total", "GWP-biogenic", "GWP-fossil", "GWP-luluc", "ODP", "POCP",
    "AP", "EP-terrestrial", "EP-freshwater", "EP-marine", "WDP",
    "ADPE", "ADPF", "HTP-c", "HTP-nc", "PM", "IR", "ETP-fw", "SQP"
])

def get_indicator_key(multilang_dict):
    if not isinstance(multilang_dict, dict):
        return None
    for lang_text in multilang_dict.values():
        for key in target_indicators:
            if re.search(rf'\b{re.escape(key)}\b', lang_text, re.IGNORECASE):
                return key
    return None

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='oekobaudat_scraper.log')
logger = logging.getLogger(__name__)

# Get database connection parameters from .env
DB_PARAMS = {
    'dbname': os.getenv("DB_NAME"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'host': os.getenv("DB_HOST"),
    'port': os.getenv("DB_PORT")
}

def connect_to_db():
    """Establish connection to PostgreSQL database"""
    try:
        return psycopg2.connect(**DB_PARAMS)
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def setup_driver():
    """Configure and return a Firefox webdriver"""
    # Set up Firefox options
    options = Options()
    options.binary_location = "/snap/firefox/5917/usr/lib/firefox/firefox"  
    # Uncomment the next line to run in headless mode
    # options.add_argument('--headless')

    # Set download preferences
    download_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    # Configure Firefox preferences for downloads
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("browser.download.dir", download_dir)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/zip")
    
    # Initialize the driver
    driver = webdriver.Firefox(options=options)
    return driver, download_dir

def set_items_per_page_to_100(driver):
    try:
        # Locate the dropdown trigger
        dropdown_trigger = WebDriverWait(driver, 10).until(
           EC.presence_of_element_located((By.CSS_SELECTOR, "div.ui-dropdown-trigger.ui-state-default.ui-corner-right.ng-tns-c62-4"))
        )
        
        # Scroll the dropdown trigger into view to avoid obstruction
        driver.execute_script("arguments[0].scrollIntoView(true);", dropdown_trigger)
        time.sleep(1)  # Allow time for scrolling
        
        # Click the dropdown trigger to open the menu
        dropdown_trigger.click()
        logger.info("Opened the items-per-page dropdown.")

        # Wait for the option with label '100' to appear and click it
        option_100 = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//li[@aria-label='100']"))
        )
        option_100.click()
        logger.info("Selected 100 items per page.")
        
        # Wait for page to reload
        time.sleep(3)
        logger.info("Set results per page to 100")
    except Exception as e:
        logger.error(f"Error setting results per page: {e}")
        raise

def download_data(driver, download_dir):
    """Scrape data from Oekobaudat website and download files."""
    base_url = "https://www.oekobaudat.de/no_cache/en/database/search.html"
    downloaded_links = set()
    global_idx = 1  # Global counter for unique filenames

    try:
        # Navigate to the website
        driver.get(base_url)
        logger.info("Navigated to the Oekobaudat website")
        
        # Wait for page to load
        time.sleep(3)

        # Set items per page to 100
        set_items_per_page_to_100(driver)

        # Start scraping pages
        page_num = 1
        while True:
            logger.info(f"Scraping page {page_num}")

            # Get all items on the current page
            items = driver.find_elements(By.CSS_SELECTOR, "a[href*='zipexport']")
            logger.info(f"Found {len(items)} items on the page")
            
            for item in items:
                try:
                    # Check if the item's href contains 'zipexport'
                    href = item.get_attribute("href")
                    if "zipexport" in href and href not in downloaded_links:
                        logger.info(f"Downloading item {global_idx} from href: {href}")
                        
                        # Download the file directly
                        response = requests.get(href, stream=True)
                        if response.status_code == 200:
                            # Save the file to the download directory
                            file_name = f"item_{global_idx}.zip"
                            file_path = os.path.join(download_dir, file_name)
                            with open(file_path, "wb") as file:
                                for chunk in response.iter_content(chunk_size=1024):
                                    file.write(chunk)
                            logger.info(f"Downloaded item {global_idx} to {file_path}")
                            downloaded_links.add(href)
                            global_idx += 1  # Increment the global counter
                        else:
                            logger.warning(f"Failed to download item {global_idx}. HTTP status code: {response.status_code}")
                    else:
                        logger.info(f"Skipping item as it does not contain 'zipexport' or already downloaded link: {href}")
                except Exception as e:
                    logger.error(f"Error processing item: {e}")
                    continue
            
            # Navigate to the next page
            if not go_to_next_page(driver):
                logger.info("No more pages to navigate.")
                break
            page_num += 1

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise

def go_to_next_page(driver):
    """Navigate to the next page."""
    try:
        # Locate the "Next" button
        next_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.ui-paginator-next:not(.ui-state-disabled)"))
        )
        
        # Scroll the "Next" button into view to avoid obstruction
        driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
        time.sleep(1)  # Allow time for scrolling

        # Click the "Next" button using JavaScript to bypass obstruction
        driver.execute_script("arguments[0].click();", next_button)
        logger.info("Navigated to the next page.")
        
        # Wait for the page to load
        time.sleep(3)
        return True
    except TimeoutException:
        logger.info("No more pages to navigate.")
        return False
    except Exception as e:
        logger.error(f"Error navigating to the next page: {e}")
        raise

def process_zip_file(zip_path):
    """Process a zip file and return parsed data."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract to temporary directory
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find the XML file in ILCD/processes/
            process_dir = os.path.join(temp_dir, 'ILCD', 'processes')
            if os.path.exists(process_dir):
                xml_files = [f for f in os.listdir(process_dir) if f.endswith('.xml')]
                
                for xml_file in xml_files:
                    xml_path = os.path.join(process_dir, xml_file)
                    # Parse XML data and return it
                    return parse_xml(xml_path)
            else:
                logger.warning(f"No ILCD/processes directory found in {zip_path}")
        
        return None
    except Exception as e:
        logger.error(f"Error processing zip file {zip_path}: {e}")
        raise

def parse_xml(xml_path):
    import xml.etree.ElementTree as ET
    import os

    tree = ET.parse(xml_path)
    root = tree.getroot()

    namespaces = {
        'common': 'http://lca.jrc.it/ILCD/Common',
        'process': 'http://lca.jrc.it/ILCD/Process',
        'epd': 'http://www.iai.kit.edu/EPD/2013',
        'epd2': 'http://www.indata.network/EPD/2019',
        'xml': 'http://www.w3.org/XML/1998/namespace'
    }

    process_id = os.path.splitext(os.path.basename(xml_path))[0]

    def get_multilang(xpath):
        return {
            el.attrib.get('{http://www.w3.org/XML/1998/namespace}lang', 'unknown'): el.text
            for el in root.findall(xpath, namespaces)
        }
    def get_multilang_from_elem(elem, xpath):
        return {
            el.attrib.get('{http://www.w3.org/XML/1998/namespace}lang', 'unknown'): el.text
            for el in elem.findall(xpath, namespaces)
        }

    def get_text(xpath):
        el = root.find(xpath, namespaces)
        return el.text if el is not None else None

    def get_text_from_elem(elem, xpath):
        el = elem.find(xpath, namespaces)
        return el.text if el is not None else None

    uuid = get_text('.//common:UUID')
    # f595f738-673f-4665-9db9-8d31b4468512_00.00.003
    # cf-4486-b17e-5031336c30ab_00.00.006
    # 57e60724-96e8-4c62-9ccc-5d3be755ec1a_00.02.000
    # if "26353b00-6cd3-426d-903b-9fc5b1670398_20.24.070" in process_id: 
    #     a = ""
    version = process_id[len(uuid) + 1:] if process_id.startswith(uuid + "_") else None

    name = get_multilang('.//process:processInformation/process:dataSetInformation/process:name/process:baseName')
    comment = get_multilang('.//process:processInformation/process:dataSetInformation/common:generalComment')
    reference_year = get_text('.//common:referenceYear')
    valid_until = get_text('.//common:dataSetValidUntil')
    time_representativeness = get_multilang('.//common:timeRepresentativenessDescription')

    safety_margins = {
        'margin': get_text('.//epd:safetyMargins/epd:margins'),
        'description': get_multilang('.//epd:safetyMargins/epd:description')
    }

    geo_location = root.find('.//process:locationOfOperationSupplyOrProduction', namespaces)
    geography = {
        'location': geo_location.attrib.get('location') if geo_location is not None else None,
        'description': get_multilang('.//process:locationOfOperationSupplyOrProduction/process:descriptionOfRestrictions')
    }

    technology_description = get_multilang('.//process:technologyDescriptionAndIncludedProcesses')
    tech_applicability = get_multilang('.//process:technologicalApplicability')

    dataset_type = get_text('.//process:LCIMethodAndAllocation/process:typeOfDataSet')
    dataset_subtype = get_text('.//process:LCIMethodAndAllocation/common:other/epd:subType')

    # Extract data sources and join them into a single string
    sources = ', '.join([
        el.find('common:shortDescription', namespaces).text
        for el in root.findall('.//process:dataSourcesTreatmentAndRepresentativeness/process:referenceToDataSource', namespaces)
    ])

    use_advice = get_multilang('.//process:dataSourcesTreatmentAndRepresentativeness/process:useAdviceForDataSet')

    reviews = []
    for review in root.findall('.//process:review', namespaces):
        reviewers = [desc.text for desc in review.findall('.//common:shortDescription', namespaces)]
        details = get_multilang('.//common:otherReviewDetails')
        reviews.append({"reviewers": reviewers, "details": details})
    
    # Extract multiple compliance entries
    compliances = []
    for compliance in root.findall('.//process:complianceDeclarations/process:compliance', namespaces):
        # Use get_multilang to extract the compliance system descriptions
        system = get_multilang_from_elem(compliance, './common:referenceToComplianceSystem/common:shortDescription')

        # Extract the approval status
        approval = compliance.find('./common:approvalOfOverallCompliance', namespaces)
        approval_text = approval.text if approval is not None else None
    
        # Append the compliance entry
        compliances.append({'system': system, 'approval': approval_text})

    admin_info = {
        'generator': get_multilang('.//process:dataGenerator/common:shortDescription'),
        'entry_by': get_multilang('.//process:dataEntryBy/common:referenceToPersonOrEntityEnteringTheData/common:shortDescription'),
        'timestamp': get_text('.//process:dataEntryBy/common:timeStamp'),
        'formats': [
            el.text for el in root.findall('.//process:dataEntryBy/common:referenceToDataSetFormat/common:shortDescription', namespaces)
        ],
        'version': get_text('.//process:publicationAndOwnership/common:dataSetVersion'),
        'license': get_text('.//process:publicationAndOwnership/common:licenseType'),
        'access': get_multilang('.//process:publicationAndOwnership/common:accessRestrictions')
    }

    classifications = []
    for c in root.findall('.//process:classificationInformation/common:classification', namespaces):
        classification_name = c.attrib.get('name', '')
        classification_levels = c.findall('./common:class', namespaces)
        for cl in classification_levels:
            level = cl.attrib['level'] = cl.attrib.get('level', '')
            classId = cl.attrib['classId'] = cl.attrib.get('classId', '')
            level_text = cl.text
            classifications.append({
                'name': classification_name,
                'level': level,
                'classId': classId,
                'classification': level_text
            })

    exchanges = []
    for exchange in root.findall('.//process:exchange', namespaces):
        data_set_internal_id = exchange.attrib.get('dataSetInternalID')
        reference_to_flow = exchange.find('.//process:referenceToFlowDataSet', namespaces)
        uri = reference_to_flow.attrib.get('uri')
        ref_object_id = reference_to_flow.attrib.get('refObjectId')
        flow = get_multilang_from_elem(exchange, './process:referenceToFlowDataSet/common:shortDescription')
        indicator_key = get_indicator_key(flow)
        direction = get_text_from_elem(exchange, './process:exchangeDirection')
        meanAmount = get_text_from_elem(exchange, './process:meanAmount')
        unit = get_text_from_elem(exchange, './/epd:referenceToUnitGroupDataSet/common:shortDescription')

        module_amounts = {}
        for amount in exchange.findall('.//epd:amount', namespaces):
            module = amount.attrib.get('{http://www.iai.kit.edu/EPD/2013}module', '')
            scenario = amount.attrib.get('{http://www.iai.kit.edu/EPD/2013}scenario', '')  
            amount_value = float(amount.text) if amount.text else None
            module_amounts[module] = {
                'amount': amount_value,
                'scenario': scenario
            }

        exchanges.append({
            'data_set_internal_id' : data_set_internal_id,
            'reference_to_flow': reference_to_flow,
            'uri': uri,
            'ref_object_id': ref_object_id,
            'flow': flow,
            'indicator_key': indicator_key,
            'direction': direction,
            'meanAmount': meanAmount,
            'unit': unit,
            'module_amounts': module_amounts
        })

    lcia_results = []
    for lcia in root.findall('.//process:LCIAResult', namespaces):
        method = get_multilang_from_elem(lcia, './process:referenceToLCIAMethodDataSet/common:shortDescription')
        indicator_key = get_indicator_key(method)
        meanAmount = get_text_from_elem(lcia, './process:meanAmount')
        unit = get_text_from_elem(lcia, './/epd:referenceToUnitGroupDataSet/common:shortDescription')

        module_amounts = {}
        for amount in lcia.findall('.//epd:amount', namespaces):
            module = amount.attrib.get('{http://www.iai.kit.edu/EPD/2013}module', '')
            scenario = amount.attrib.get('{http://www.iai.kit.edu/EPD/2013}scenario', '')  
            amount_value = float(amount.text) if amount.text else None
            module_amounts[module] = {
                'amount': amount_value,
                'scenario': scenario
            }

        lcia_results.append({
            'method': method,
            'indicator_key': indicator_key,
            'meanAmount': meanAmount,
            'unit': unit,
            'module_amounts': module_amounts
        })


    # Extract the referenceToReferenceFlow ID
    reference_flow_id = root.find('.//process:quantitativeReference/process:referenceToReferenceFlow', namespaces).text


    reference_flow = []
    for exchange in exchanges:
        if exchange['data_set_internal_id'] == reference_flow_id:

            # Get the directory of the original xml file and set final_uri to None
            parent_folder = os.path.dirname(xml_path)
            final_uri = None

            # Check if the exchange has a URI or a reference to a flow
            uri = exchange['uri']
            refObjectId = exchange['ref_object_id']

            if uri:
                base_uri = os.path.splitext(os.path.basename(uri))[0]  # Remove the .xml extension

                # Get the directory where to look for the file
                target_dir = os.path.normpath(os.path.join(parent_folder, os.path.dirname(uri)))

                # Look for files matching the pattern
                matching_files = []
                if os.path.exists(target_dir):
                    for filename in os.listdir(target_dir):
                        if filename.startswith(base_uri) and filename.endswith('.xml'):
                            matching_files.append(filename)
    

                # Get the first matching file if any exists
                if matching_files:
                    # Sort to ensure consistent behavior
                    matching_files.sort()
                    final_uri = os.path.join(target_dir, matching_files[0])
            elif refObjectId:

                # Change 'processes' to 'flows' in the path
                flows_dir = os.path.join(os.path.dirname(parent_folder), 'flows')
                
                # Look for the file with the refObjectId
                if os.path.exists(flows_dir):
                    for filename in os.listdir(flows_dir):
                        if filename.startswith(refObjectId) and filename.endswith('.xml'):
                            final_uri = os.path.join(flows_dir, filename)
                            break

            if final_uri and os.path.exists(final_uri):
                # Parse the referenced XML file
                referenced_tree = ET.parse(final_uri)
                referenced_root = referenced_tree.getroot()

                # Extract flow properties
                flow_properties = []

                # Get the reference flow property ID
                ref_flow_prop_id_node = referenced_root.find('.//referenceToReferenceFlowProperty', namespaces={'': 'http://lca.jrc.it/ILCD/Flow'})
                ref_flow_prop_id = ref_flow_prop_id_node.text.strip() if ref_flow_prop_id_node is not None else None

                for flow_prop in referenced_root.findall('.//flowProperty', namespaces={'': 'http://lca.jrc.it/ILCD/Flow'}):
                    flow_entry = {}

                    dataSetInternalID = flow_prop.attrib.get('dataSetInternalID', '').strip()

                    # Extract name_en and name_de
                    ref_to_flow_prop = flow_prop.find('./referenceToFlowPropertyDataSet', namespaces={'': 'http://lca.jrc.it/ILCD/Flow'})
                    if ref_to_flow_prop is not None:
                        names = get_multilang_from_elem(ref_to_flow_prop, './common:shortDescription')
                        flow_entry['name_en'] = names.get('en')
                        flow_entry['name_de'] = names.get('de')
                    else:
                        flow_entry['name_en'] = None
                        flow_entry['name_de'] = None

                    # Extract mean value
                    mean_value_node = flow_prop.find('./meanValue', namespaces={'': 'http://lca.jrc.it/ILCD/Flow'})
                    flow_entry['mean_value'] = float(mean_value_node.text.strip()) if mean_value_node is not None and mean_value_node.text else None

                    # Map unit based on name
                    if (flow_entry['name_en'] and 'volume' in flow_entry['name_en'].lower()) or \
                    (flow_entry['name_de'] and 'volumen' in flow_entry['name_de'].lower())or \
                    (flow_entry['name_de'] and 'volume' in flow_entry['name_de'].lower()):
                        flow_entry['unit'] = 'm3'
                    elif (flow_entry['name_en'] and 'mass' in flow_entry['name_en'].lower()) or \
                        (flow_entry['name_de'] and 'masse' in flow_entry['name_de'].lower()):
                        flow_entry['unit'] = 'kg'
                    elif (flow_entry['name_en'] and 'weight' in flow_entry['name_en'].lower()) or \
                        (flow_entry['name_de'] and 'gewicht' in flow_entry['name_de'].lower()):
                        flow_entry['unit'] = 'kg'
                    elif (flow_entry['name_en'] and 'area' in flow_entry['name_en'].lower()) or \
                        (flow_entry['name_de'] and 'fläche' in flow_entry['name_de'].lower()):
                        flow_entry['unit'] = 'm2'
                    elif (flow_entry['name_en'] and 'length' in flow_entry['name_en'].lower()) or \
                        (flow_entry['name_de'] and 'länge' in flow_entry['name_de'].lower()):
                        flow_entry['unit'] = 'm'
                    elif (flow_entry['name_en'] and 'piece' in flow_entry['name_en'].lower()) or \
                        (flow_entry['name_de'] and 'stück' in flow_entry['name_de'].lower()):
                        flow_entry['unit'] = 'pcs'
                    else:
                        flow_entry['unit'] = 'unknown'

                    # Set reference flag
                    flow_entry['is_reference'] = (dataSetInternalID == ref_flow_prop_id)

                    # Optional: include the internal ID in the record
                    flow_entry['dataSetInternalID'] = dataSetInternalID

                    flow_properties.append(flow_entry)


                # Extract PropertyData and PropertyDetails
                material_data = {}
                for property_data in referenced_root.findall('.//mm:PropertyData', namespaces={'mm': 'http://www.matml.org/'}):
                    property_id = property_data.attrib.get('property')
                    data_value = property_data.find('./mm:Data', namespaces={'mm': 'http://www.matml.org/'}).text
                    material_data[property_id] = {'value': data_value}

                for property_details in referenced_root.findall('.//mm:PropertyDetails', namespaces={'mm': 'http://www.matml.org/'}):
                    property_id = property_details.attrib.get('id')
                    if property_id in material_data:
                        material_data[property_id].update({
                            'name': property_details.find('./mm:Name', namespaces={'mm': 'http://www.matml.org/'}).text,
                            'units': property_details.find('./mm:Units', namespaces={'mm': 'http://www.matml.org/'}).attrib.get('name'),
                            'description': property_details.find('./mm:Units', namespaces={'mm': 'http://www.matml.org/'}).attrib.get('description')
                        })

                reference_flow.append({
                    'material_properties': material_data,
                    'flow_properties': flow_properties
                })

    return {
        'process_id': process_id,
        'uuid': uuid,
        'version': version,
        'name': name,
        'description': comment,
        'classifications': classifications,
        'reference_year': reference_year,
        'valid_until': valid_until,
        'time_representativeness': time_representativeness,
        'safety_margins': safety_margins,
        'geography': geography,
        'technology_description': technology_description,
        'tech_applicability': tech_applicability,
        'dataset_type': dataset_type,
        'dataset_subtype': dataset_subtype,
        'sources': sources,
        'use_advice': use_advice,
        'reviews': reviews,
        'compliances': compliances, 
        'admin_info': admin_info,
        'exchanges': exchanges,
        'lcia_results': lcia_results,
        'reference_flow': reference_flow
    }

def store_data(download_dir):
    """Process files in the downloads folder and store data in the database."""
    conn = None
    try:
        conn = connect_to_db()
        logger.info(f"Connected to database {DB_PARAMS['dbname']} on {DB_PARAMS['host']}")

        # Counter to track the number of files processed
        file_count = 0
    
        # Loop through all zip files in the downloads folder
        for file_name in os.listdir(download_dir):
            if file_name.endswith(".zip"):
                file_path = os.path.join(download_dir, file_name)
                logger.info(f"Processing file: {file_path}")
                
                # Process the zip file and extract data
                item_data = process_zip_file(file_path)
                if item_data:
                    store_data_in_db([item_data], conn)  # Store the data in the database
                    logger.info(f"Data from {file_name} stored successfully.")
                else:
                    logger.warning(f"No data extracted from {file_name}. Skipping.")

                # Increment the file counter
                file_count += 1

                # Stop processing after 50 files
                if file_count >= 50:
                    logger.info("Processed 100 files. Stopping further processing.")
                    break                

    except Exception as e:
        logger.error(f"Error storing data in the database: {e}")
        raise
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")

def store_data_in_db(collected_data, conn):
    with conn.cursor() as cursor:
        for item in collected_data:
            # Check if the product with the given process_id already exists
            cursor.execute('''
                SELECT 1 FROM products WHERE process_id = %s
            ''', (item['process_id'],))
            exists = cursor.fetchone()

            if exists:
                logger.info(f"Product with process_id {item['process_id']} already exists. Skipping insertion.")
                continue

            # Insert the product if it does not exist
            cursor.execute('''
                INSERT INTO products (
                    process_id, uuid, version, name_de, name_en, description_de, description_en, reference_year,
                    valid_until, time_repr_de, time_repr_en, safety_margin, safety_descr_de, safety_descr_en,
                    geo_location, geo_descr_de, geo_descr_en,
                    tech_descr_de, tech_descr_en, tech_applic_de, tech_applic_en,
                    dataset_type, dataset_subtype, sources,
                    use_advice_de, use_advice_en,
                    generator_de, generator_en, entry_by_de, entry_by_en,
                    admin_version, license_type, access_de, access_en,
                    timestamp, formats
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s,
                          %s, %s, %s,
                          %s, %s, %s, %s, 
                          %s, %s, %s,
                          %s, %s,
                          %s, %s, %s, %s,
                          %s, %s, %s, %s,
                          %s, %s)
            ''', (
                item['process_id'], item['uuid'], item['version'],
                item['name'].get('de'), item['name'].get('en'),
                item['description'].get('de'), item['description'].get('en'),
                item['reference_year'], item['valid_until'],
                item['time_representativeness'].get('de'), item['time_representativeness'].get('en'),
                item['safety_margins']['margin'],
                item['safety_margins']['description'].get('de'), item['safety_margins']['description'].get('en'),
                item['geography']['location'],
                item['geography']['description'].get('de'), item['geography']['description'].get('en'),
                item['technology_description'].get('de'), item['technology_description'].get('en'),
                item['tech_applicability'].get('de'), item['tech_applicability'].get('en'),
                item['dataset_type'], item['dataset_subtype'], item['sources'],
                item['use_advice'].get('de'), item['use_advice'].get('en'),
                item['admin_info']['generator'].get('de'), item['admin_info']['generator'].get('en'),
                item['admin_info']['entry_by'].get('de'), item['admin_info']['entry_by'].get('en'),
                item['admin_info']['version'], item['admin_info']['license'],
                item['admin_info']['access'].get('de'), item['admin_info']['access'].get('en'),
                item['admin_info']['timestamp'],
                ', '.join(item['admin_info']['formats'])  # Join the list of formats into a single string
            ))

            # Insert related data (e.g., classifications, exchanges, LCIA results, reviews, compliances)
            for classification in item['classifications']:
                cursor.execute('''
                    INSERT INTO classifications (process_id, name, level, classId, classification)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (item['process_id'], classification['name'], classification['level'], classification['classId'], classification['classification']))

            for exchange in item['exchanges']:
                cursor.execute('''
                    INSERT INTO exchanges (process_id, flow_de, flow_en, indicator_key, direction, meanAmount, unit)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING exchange_id
                ''', (
                    item['process_id'],
                    exchange['flow'].get('de'),
                    exchange['flow'].get('en'),
                    exchange['indicator_key'],
                    exchange['direction'],
                    exchange['meanAmount'],
                    exchange['unit']
                ))
                exchange_id = cursor.fetchone()[0]

                for module, data in exchange['module_amounts'].items():
                   scenario = data['scenario']
                   amount = data['amount']
                   cursor.execute('''
                       INSERT INTO exchange_moduleamounts (exchange_id, module, scenario, amount)
                       VALUES (%s, %s, %s, %s)
                   ''', (exchange_id, module, scenario, amount))

            for lcia in item['lcia_results']:
                cursor.execute('''
                    INSERT INTO lcia_results (process_id, method_de, method_en, indicator_key, meanAmount, unit)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING lcia_id
                ''', (
                    item['process_id'],
                    lcia['method'].get('de'),
                    lcia['method'].get('en'),
                    lcia['indicator_key'],
                    lcia['meanAmount'],
                    lcia['unit']
                ))
                lcia_id = cursor.fetchone()[0]

                for module, data in lcia['module_amounts'].items():
                    scenario = data['scenario']
                    amount = data['amount']
                    cursor.execute('''
                        INSERT INTO lcia_moduleamounts (lcia_id, module, scenario, amount)
                        VALUES (%s, %s, %s, %s)
                    ''', (lcia_id, module, scenario, amount))

            for review in item['reviews']:
                for reviewer in review['reviewers']:
                    cursor.execute('''
                        INSERT INTO reviews (process_id, reviewer, detail_de, detail_en)
                        VALUES (%s, %s, %s, %s)
                    ''', (
                        item['process_id'], reviewer,
                        review['details'].get('de'), review['details'].get('en')
                    ))

            for compliance in item['compliances']:
                cursor.execute('''
                    INSERT INTO compliances (process_id, system_de, system_en, approval)
                    VALUES (%s, %s, %s, %s)
                ''', (
                    item['process_id'],
                    compliance['system'].get('de'), compliance['system'].get('en'),
                    compliance['approval']
                ))

            for refFlow in item['reference_flow']:

                # Insert the reference flow properties 
                for flow_property in refFlow['flow_properties']:
                    cursor.execute('''
                        INSERT INTO flow_properties (process_id, name_en, name_de, meanamount, unit, is_reference)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (
                        item['process_id'],
                        flow_property.get('name_en'),
                        flow_property.get('name_de'),
                        flow_property.get('mean_value'),
                        flow_property.get('unit'),
                        flow_property.get('is_reference', False)
                    ))

                # Insert the material properties 
                for property_id, property_data in refFlow['material_properties'].items():
                    cursor.execute('''
                        INSERT INTO material_properties (process_id, property_id, property_name, value, units, description)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (
                        item['process_id'],
                        property_id,
                        property_data.get('name'),
                        convert_to_float(property_data.get('value')),
                        property_data.get('units'),
                        property_data.get('description')
                    ))
                    
        conn.commit()

def convert_to_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
    
def main():
    """Main function to run the scraper."""
    driver = None
    download_dir = os.path.join(os.getcwd(), "downloads")
    
    try:
        # Set up the webdriver
        #driver, download_dir = setup_driver()
        logger.info("WebDriver setup complete")
        
        # Run the scraper and download files
        #download_data(driver, download_dir)
        logger.info("Scraping and downloading completed successfully")
        
        # Process the downloaded files and store the data in the database
        store_data(download_dir)
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")
    finally:
        # Clean up
        if driver:
            driver.quit()
        logger.info("Resources cleaned up. Scraping process ended.")

if __name__ == "__main__":
    main()