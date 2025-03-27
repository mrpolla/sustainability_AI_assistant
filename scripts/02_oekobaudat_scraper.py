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
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def setup_driver():
    """Configure and return a Firefox webdriver"""
    # Set up Firefox options
    options = Options()
    # Uncomment the next line to run in headless mode
    # options.add_argument('--headless')

   # Specify the Firefox binary path if necessary
    options.binary_location = "/snap/firefox/5917/usr/lib/firefox/firefox"  # Update this path if Firefox is installed elsewhere
     
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

def scrape_oekobaudat(driver, download_dir):
    """Scrape data from Oekobaudat website and return collected data"""
    base_url = "https://www.oekobaudat.de/no_cache/en/database/search.html"
    collected_data = []  # List to store all collected items

    try:
        # Navigate to the website
        driver.get(base_url)
        logger.info("Navigated to the Oekobaudat website")
        
        # Wait for page to load
        time.sleep(3)

        # Get all items on the current page
        items = driver.find_elements(By.CSS_SELECTOR, "a[href*='zipexport']")
        logger.info(f"Found {len(items)} items on the page")
        
        for idx, item in enumerate(items, 1):
            if idx > 1:
                break
            try:
                # Check if the item's href contains 'zipexport'
                href = item.get_attribute("href")
                if "zipexport" in href:
                    logger.info(f"Downloading item {idx} from href: {href}")
                    
                    # Download the file directly
                    response = requests.get(href, stream=True)
                    if response.status_code == 200:
                        # Save the file to the download directory
                        file_name = f"item_{idx}.zip"
                        file_path = os.path.join(download_dir, file_name)
                        with open(file_path, "wb") as file:
                            for chunk in response.iter_content(chunk_size=1024):
                                file.write(chunk)
                        logger.info(f"Downloaded item {idx} to {file_path}")
                        
                        # Process the downloaded zip file and collect data
                        item_data = process_latest_zip(download_dir)
                        if item_data:
                            collected_data.append(item_data)
                    else:
                        logger.warning(f"Failed to download item {idx}. HTTP status code: {response.status_code}")
                else:
                    logger.info(f"Skipping item {idx} as it does not contain 'zipexport'")
            
            except Exception as e:
                logger.error(f"Error processing item {idx}: {e}")
                continue
            
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise
    finally:
        # Clean up downloads directory
        for file in os.listdir(download_dir):
            file_path = os.path.join(download_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
    
    return collected_data

def select_items_per_page(driver):
    """Set the number of items per page to 100"""
    try:
        # Find and click on the items per page dropdown
        dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "select.items-per-page"))
        )
        dropdown.click()
        
        # Select 100 items per page
        option_100 = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "select.items-per-page option[value='100']"))
        )
        option_100.click()
        
        # Wait for page to reload
        time.sleep(3)
        logger.info("Set items per page to 100")
    except TimeoutException:
        logger.error("Timeout while trying to set items per page")
        raise

def get_total_pages(driver):
    """Get the total number of pages"""
    try:
        pagination = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.pagination"))
        )
        
        # Find all page links and get the highest number
        page_links = pagination.find_elements(By.CSS_SELECTOR, "li a")
        page_numbers = []
        
        for link in page_links:
            try:
                page_num = int(link.text.strip())
                page_numbers.append(page_num)
            except ValueError:
                # Skip non-numeric links (like "Next" or "Previous")
                continue
        
        if page_numbers:
            return max(page_numbers)
        else:
            return 1  # Default to 1 page
    except TimeoutException:
        logger.error("Timeout while trying to get total pages")
        raise

def go_to_page(driver, page_num):
    """Navigate to a specific page number"""
    try:
        pagination = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.pagination"))
        )
        
        # Find the link corresponding to the page number
        page_links = pagination.find_elements(By.CSS_SELECTOR, "li a")
        
        for link in page_links:
            if link.text.strip() == str(page_num):
                link.click()
                # Wait for page to load
                time.sleep(3)
                return
        
        # If we didn't find the exact page, try using Next button
        next_buttons = pagination.find_elements(By.XPATH, "//a[contains(text(), 'Next') or contains(@aria-label, 'Next')]")
        if next_buttons:
            next_buttons[0].click()
            # Wait for page to load
            time.sleep(3)
            # Recursive call to find the page
            go_to_page(driver, page_num)
        else:
            logger.error(f"Couldn't find page {page_num}")
            raise Exception(f"Navigation to page {page_num} failed")
    except TimeoutException:
        logger.error(f"Timeout while trying to navigate to page {page_num}")
        raise

def process_latest_zip(download_dir):
    """Process the most recently downloaded zip file and return parsed data"""
    try:
        # Find the latest zip file
        zip_files = [f for f in os.listdir(download_dir) if f.endswith('.zip')]
        if not zip_files:
            logger.warning("No zip files found in download directory")
            return None
        
        # Sort by modification time (newest first)
        latest_zip = sorted(zip_files, key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)[0]
        zip_path = os.path.join(download_dir, latest_zip)
        
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
                logger.warning(f"No ILCD/processes directory found in {latest_zip}")
        
        # Remove the processed zip file
        os.remove(zip_path)
    
    except Exception as e:
        logger.error(f"Error processing zip file: {e}")
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

    def get_text(xpath):
        el = root.find(xpath, namespaces)
        return el.text if el is not None else None

    uuid = get_text('.//common:UUID')
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
    tech_diagram = get_multilang('.//process:referenceToTechnologyFlowDiagrammOrPicture/common:shortDescription')

    dataset_type = get_text('.//process:LCIMethodAndAllocation/typeOfDataSet')
    dataset_subtype = get_text('.//process:LCIMethodAndAllocation/common:other/epd:subType')

    sources = [el.findtext('common:shortDescription', namespaces=namespaces) for el in root.findall('.//process:dataSourcesTreatmentAndRepresentativeness/referenceToDataSource', namespaces)]
    use_advice = get_multilang('.//process:dataSourcesTreatmentAndRepresentativeness/process:useAdviceForDataSet')

    reviews = []
    for review in root.findall('.//process:review', namespaces):
        reviewers = [desc.text for desc in review.findall('.//common:shortDescription', namespaces)]
        details = get_multilang('.//common:otherReviewDetails')
        reviews.append({"reviewers": reviewers, "details": details})

    compliance = {
        'system': get_multilang('.//process:complianceDeclarations/common:referenceToComplianceSystem/common:shortDescription'),
        'approval': get_text('.//process:complianceDeclarations/common:approvalOfOverallCompliance')
    }

    admin_info = {
        'generator': get_multilang('.//process:dataGenerator/common:shortDescription'),
        'entry_by': get_multilang('.//process:dataEntryBy/common:shortDescription'),
        'version': get_text('.//process:publicationAndOwnership/common:dataSetVersion'),
        'license': get_text('.//process:publicationAndOwnership/common:licenseType'),
        'access': get_multilang('.//process:publicationAndOwnership/common:accessRestrictions')
    }

    classification = []
    for c in root.findall('.//common:classificationInformation/common:classification', namespaces):
        sys = c.attrib.get('name', '')
        levels = [f"{cl.attrib.get('level', '')}:{cl.text}" for cl in c.findall('./common:class', namespaces)]
        classification.append(f"{sys}:{'|'.join(levels)}")

    exchanges = []
    for exchange in root.findall('.//process:exchange', namespaces):
        flow = get_multilang('./process:referenceToFlowDataSet/common:shortDescription')
        direction = get_text('./process:exchangeDirection')
        meanAmount = get_text('./process:meanAmount')
        unit = get_text('.//epd:referenceToUnitGroupDataSet/common:shortDescription')

        module_amounts = {}
        for amount in exchange.findall('.//epd:amount', namespaces):
            module = amount.attrib.get('{http://www.iai.kit.edu/EPD/2013}module', '')
            module_amounts[module] = float(amount.text) if amount.text else 0.0

        exchanges.append({
            'flow': flow,
            'direction': direction,
            'meanAmount': meanAmount,
            'unit': unit,
            'module_amounts': module_amounts
        })

    lcia_results = []
    for lcia in root.findall('.//process:LCIAResult', namespaces):
        method = get_multilang('./process:referenceToLCIAMethodDataSet/common:shortDescription')
        meanAmount = get_text('./process:meanAmount')
        unit = get_text('.//epd:referenceToUnitGroupDataSet/common:shortDescription')

        module_amounts = {}
        for amount in lcia.findall('.//epd:amount', namespaces):
            module = amount.attrib.get('{http://www.iai.kit.edu/EPD/2013}module', '')
            module_amounts[module] = float(amount.text) if amount.text else 0.0

        lcia_results.append({
            'method': method,
            'meanAmount': meanAmount,
            'unit': unit,
            'module_amounts': module_amounts
        })

    return {
        'process_id': process_id,
        'uuid': uuid,
        'version': version,
        'name': name,
        'description': comment,
        'classification': classification,
        'reference_year': reference_year,
        'valid_until': valid_until,
        'time_representativeness': time_representativeness,
        'safety_margins': safety_margins,
        'geography': geography,
        'technology_description': technology_description,
        'tech_applicability': tech_applicability,
        'tech_diagram': tech_diagram,
        'dataset_type': dataset_type,
        'dataset_subtype': dataset_subtype,
        'sources': sources,
        'use_advice': use_advice,
        'reviews': reviews,
        'compliance': compliance,
        'admin_info': admin_info,
        'exchanges': exchanges,
        'lcia_results': lcia_results
    }



# def list_tables(conn):
#     """List all tables in the current schema."""
#     try:
#         with conn.cursor() as cursor:
#             cursor.execute("""
#                 SELECT table_name
#                 FROM information_schema.tables
#                 WHERE table_schema = 'public'
#                 ORDER BY table_name;
#             """)
#             tables = cursor.fetchall()
#             logger.info("Tables in the database:")
#             for table in tables:
#                 logger.info(f"- {table[0]}")
#             return [table[0] for table in tables]
#     except Exception as e:
#         logger.error(f"Error listing tables: {e}")
#         raise

def store_data_in_db(collected_data, conn):
    with conn.cursor() as cursor:
        for item in collected_data:
            cursor.execute('''
                INSERT INTO products (
                    process_id, uuid, version, name_de, name_en, description_de, description_en, reference_year,
                    valid_until, time_repr_de, time_repr_en, safety_margin, safety_descr_de, safety_descr_en,
                    geo_location, geo_descr_de, geo_descr_en,
                    tech_descr_de, tech_descr_en, tech_applic_de, tech_applic_en, tech_diagram_de, tech_diagram_en,
                    dataset_type, dataset_subtype,
                    source1, source2, source3,
                    use_advice_de, use_advice_en,
                    compliance_de, compliance_en, approval,
                    generator_de, generator_en, entry_by_de, entry_by_en,
                    admin_version, license_type, access_de, access_en
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s,
                          %s, %s, %s,
                          %s, %s, %s, %s, %s, %s,
                          %s, %s,
                          %s, %s, %s,
                          %s, %s,
                          %s, %s, %s,
                          %s, %s, %s, %s,
                          %s, %s, %s, %s)
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
                item['tech_diagram'].get('de'), item['tech_diagram'].get('en'),
                item['dataset_type'], item['dataset_subtype'],
                (item['sources'][0] if len(item['sources']) > 0 else None),
                (item['sources'][1] if len(item['sources']) > 1 else None),
                (item['sources'][2] if len(item['sources']) > 2 else None),
                item['use_advice'].get('de'), item['use_advice'].get('en'),
                item['compliance']['system'].get('de'), item['compliance']['system'].get('en'), item['compliance']['approval'],
                item['admin_info']['generator'].get('de'), item['admin_info']['generator'].get('en'),
                item['admin_info']['entry_by'].get('de'), item['admin_info']['entry_by'].get('en'),
                item['admin_info']['version'], item['admin_info']['license'],
                item['admin_info']['access'].get('de'), item['admin_info']['access'].get('en')
            ))

            for classification in item['classification']:
                cursor.execute('''
                    INSERT INTO classifications (process_id, classification)
                    VALUES (%s, %s)
                ''', (item['process_id'], classification))

            for exchange in item['exchanges']:
                cursor.execute('''
                    INSERT INTO exchanges (process_id, flow_de, flow_en, direction, meanAmount, unit)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING exchange_id
                ''', (
                    item['process_id'],
                    exchange['flow'].get('de'),
                    exchange['flow'].get('en'),
                    exchange['direction'],
                    exchange['meanAmount'],
                    exchange['unit']
                ))
                exchange_id = cursor.fetchone()[0]

                for module, amount in exchange['module_amounts'].items():
                    cursor.execute('''
                        INSERT INTO exchange_moduleamounts (exchange_id, module, amount)
                        VALUES (%s, %s, %s)
                    ''', (exchange_id, module, amount))

            for lcia in item['lcia_results']:
                cursor.execute('''
                    INSERT INTO lcia_results (process_id, method_de, meanAmount, unit)
                    VALUES (%s, %s, %s, %s)
                    RETURNING lcia_id
                ''', (
                    item['process_id'],
                    lcia['method'].get('de'),
                    lcia['meanAmount'],
                    lcia['unit']
                ))
                lcia_id = cursor.fetchone()[0]

                for module, amount in lcia['module_amounts'].items():
                    cursor.execute('''
                        INSERT INTO lcia_moduleamounts (lcia_id, module, amount)
                        VALUES (%s, %s, %s)
                    ''', (lcia_id, module, amount))

            for review in item['reviews']:
                for reviewer in review['reviewers']:
                    cursor.execute('''
                        INSERT INTO reviews (process_id, reviewer, detail_de, detail_en)
                        VALUES (%s, %s, %s, %s)
                    ''', (
                        item['process_id'], reviewer,
                        review['details'].get('de'), review['details'].get('en')
                    ))

        conn.commit()

def main():
    """Main function to run the scraper"""
    driver = None
    conn = None
    download_dir = None
    
    try:
        # Set up the webdriver
        driver, download_dir = setup_driver()
        logger.info("WebDriver setup complete")
        
        # Run the scraper and collect data
        collected_data = scrape_oekobaudat(driver, download_dir)
        logger.info("Scraping completed successfully")
        
        # Connect to database and store data
        conn = connect_to_db()
        # tables = list_tables(conn)
        logger.info(f"Connected to database {DB_PARAMS['dbname']} on {DB_PARAMS['host']}")
        store_data_in_db(collected_data, conn)
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")
    finally:
        # Clean up
        if driver:
            driver.quit()
        if conn:
            conn.close()
        logger.info("Resources cleaned up. Scraping process ended.")

if __name__ == "__main__":
    main()