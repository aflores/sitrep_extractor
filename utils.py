"""
Utility functions for web scraping and data extraction.
Contains functions related to HTTP requests, BeautifulSoup parsing, and data processing.
"""

import requests
import io
import re
import tempfile
import os
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.section import WD_SECTION
## from PIL.ImageFont import FreeTypeFont
from config import (
    NWS_FORECAST_OFFICES,
    NWS_BASE_URL,
    NWS_DESCRIPTION_SELECTOR,
    NO_CAPTION,
    NO_IMAGE,
    NHC_URL,
    NHC_7DAY_IMG_URL,
    FIRE_DANGER_IMAGE_URL,
    TITLE,
    OUTPUT_FILE_NAME
)

# Set up external requests logger
def setup_external_requests_logger():
    """Set up logger specifically for external HTTP requests"""
    
    # Create logs directory if it doesn't exist
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Create external requests logger
    ext_logger = logging.getLogger('external_requests')
    ext_logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if not ext_logger.handlers:
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # File handler for external requests
        file_handler = logging.FileHandler(f'{logs_dir}/external_requests.log')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        ext_logger.addHandler(file_handler)
        ext_logger.addHandler(console_handler)
    
    return ext_logger

# Initialize the external requests logger
external_logger = setup_external_requests_logger()


def request_page(url):
    """
    Fetch a page and return the text in the response with comprehensive logging.
    
    Args:
        url (str): The URL to fetch
        
    Returns:
        str or None: The response text if successful, None if there was an error
    """
    start_time = datetime.now()
    
    try:
        external_logger.info(f"HTTP REQUEST START - URL: {url}")
        
        # Make the request with timeout
        response = requests.get(url, timeout=30)
        
        # Calculate response time
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Log response details
        external_logger.info(
            f"HTTP REQUEST SUCCESS - URL: {url} - "
            f"Status: {response.status_code} - "
            f"Time: {response_time:.2f}ms - "
            f"Size: {len(response.content)} bytes - "
            f"Content-Type: {response.headers.get('content-type', 'Unknown')}"
        )
        
        response.raise_for_status()
        return response.text
        
    except requests.exceptions.Timeout:
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        external_logger.error(f"HTTP REQUEST TIMEOUT - URL: {url} - Time: {response_time:.2f}ms")
        return None
        
    except requests.exceptions.RequestException as e:
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        external_logger.error(
            f"HTTP REQUEST ERROR - URL: {url} - "
            f"Error: {str(e)} - "
            f"Time: {response_time:.2f}ms"
        )
        return None
        
    except Exception as e:
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        external_logger.error(
            f"HTTP REQUEST EXCEPTION - URL: {url} - "
            f"Exception: {str(e)} - "
            f"Time: {response_time:.2f}ms"
        )
        return None


def extract_nws_info(nws_response):
    """
    Obtain the description from the bottom of the first image on the response and the URL of the image.
    
    Args:
        nws_response (str): HTML response content from NWS page
        
    Returns:
        dict: Dictionary containing 'description' and 'image_url'
    """
    if not nws_response:
        return {"description": "*** ERROR FETCHING PAGE ***", "image_url": None}
    
    soup = BeautifulSoup(nws_response, 'html.parser')
    desc_element = soup.select_one(NWS_DESCRIPTION_SELECTOR)
    
    if desc_element:
        desc = desc_element.text.strip().replace('Click/tap image to enlarge | ','')
    else:
        desc = NO_CAPTION
    
    # Check if a description is provided
    if len(desc) == 0:
        desc = NO_CAPTION 
    
    # Get the url of the first image in the page
    img_element = soup.select_one('div.graphicast img')
    img_url = img_element.attrs['src'] if img_element else None

    return {"description": desc, "image_url": img_url}

def create_image(size, bgColor, message, font, fontColor):
    W, H = size
    image = Image.new('RGB', size, bgColor)
    draw = ImageDraw.Draw(image)
    _, _, w, h = draw.textbbox((0, 0), message, font=font)
    draw.text(((W-w)/2, (H-h)/2), message, font=font, fill=fontColor)
    return image

def show_image_error():
    """
    Create a simple error image when image fetching fails.
    
    Returns:
        io.BytesIO: Image stream containing error image
    """
    # Create a simple error image
    message = NO_IMAGE 
    font = ImageFont.load_default(size=25)
    image = create_image((600,400), 'lightyellow',message,font,'black')
  
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr


def get_image(img_url):
    """
    Fetch an image and return it as stream with comprehensive logging.
    
    Args:
        img_url (str): URL of the image to fetch
        
    Returns:
        io.BytesIO: Image stream
    """
    if not img_url:
        external_logger.warning("IMAGE REQUEST - No URL provided, returning error image")
        return show_image_error()
    
    start_time = datetime.now()
    
    try:
        external_logger.info(f"IMAGE REQUEST START - URL: {img_url}")
        
        # Make the request with timeout
        response = requests.get(img_url, timeout=30)
        
        # Calculate response time
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Log response details
        external_logger.info(
            f"IMAGE REQUEST SUCCESS - URL: {img_url} - "
            f"Status: {response.status_code} - "
            f"Time: {response_time:.2f}ms - "
            f"Size: {len(response.content)} bytes - "
            f"Content-Type: {response.headers.get('content-type', 'Unknown')}"
        )
        
        response.raise_for_status()
        
        # Validate that we actually got an image
        content_type = response.headers.get('content-type', '').lower()
        if not any(img_type in content_type for img_type in ['image/', 'application/octet-stream']):
            external_logger.warning(
                f"IMAGE REQUEST WARNING - URL: {img_url} - "
                f"Unexpected content type: {content_type}"
            )
        
        image_stream = io.BytesIO(response.content)
        image_stream.seek(0)
        return image_stream
        
    except requests.exceptions.Timeout:
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        external_logger.error(f"IMAGE REQUEST TIMEOUT - URL: {img_url} - Time: {response_time:.2f}ms")
        return show_image_error()
        
    except requests.exceptions.RequestException as e:
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        external_logger.error(
            f"IMAGE REQUEST ERROR - URL: {img_url} - "
            f"Error: {str(e)} - "
            f"Time: {response_time:.2f}ms"
        )
        return show_image_error()
        
    except Exception as e:
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        external_logger.error(
            f"IMAGE REQUEST EXCEPTION - URL: {img_url} - "
            f"Exception: {str(e)} - "
            f"Time: {response_time:.2f}ms"
        )
        return show_image_error()


def extract_text_arrays_from_url(url):
    """
    Extract description of items in NHC Seven-day Graphical Tropical Weather Outlook.
    Uses Selenium to fetch dynamically loaded content and BeautifulSoup to parse.
    
    Args:
        url (str): URL to extract text arrays from
        
    Returns:
        list: List of extracted text descriptions
    """
    nhc_text = []
    start_time = datetime.now()
    driver = None
    
    try:
        external_logger.info(f"SELENIUM REQUEST START - URL: {url}")
        
        # Set up Selenium with headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)

        # Fetch the fully loaded page
        driver.get(url)
        page_source = driver.page_source
        page_load_time = (datetime.now() - start_time).total_seconds() * 1000
        
        external_logger.info(
            f"SELENIUM PAGE LOADED - URL: {url} - "
            f"Time: {page_load_time:.2f}ms - "
            f"Page size: {len(page_source)} chars"
        )
        
        driver.quit()
        driver = None

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')

        # Find all <script> tags
        script_tags = soup.find_all('script')
        external_logger.debug(f"SELENIUM PARSING - URL: {url} - Found {len(script_tags)} script tags")

        # Regex pattern to find arrays named 'Text'
        pattern = r'Text\[\d+\]\s*=\s*\[([^\]]*)\]'

        found_arrays = []
        for script in script_tags:
            if script.string:
                matches = re.finditer(pattern, script.string, re.MULTILINE)
                found_arrays.extend([match.group(1).strip() for match in matches])

        external_logger.info(f"SELENIUM TEXT EXTRACTION - URL: {url} - Found {len(found_arrays)} text arrays")

        if found_arrays:
            for idx, content in enumerate(found_arrays, 1):
                items = re.split(r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)', content)
                clean_items = []
                for item in items:
                    item = item.strip().strip("'").strip('"')
                    if item:
                        soup = BeautifulSoup(item, 'html.parser')
                        sub_items = []
                        for element in soup.find_all(string=True, recursive=True):
                            text = element.strip()
                            if text:
                                sub_texts = text.split('\n')
                                for sub_text in sub_texts:
                                    sub_text = sub_text.strip()
                                    if sub_text:
                                        sub_text = sub_text.replace('(click for details)', '').strip()
                                        if sub_text:
                                            sub_items.append(sub_text)
                        clean_items.extend(sub_items)
                paragraph = '\n'.join(clean_items).strip()
                nhc_text.append(paragraph)
        else:
            nhc_text.append("No tropical weather outlook data available")
            external_logger.warning(f"SELENIUM NO DATA - URL: {url} - No tropical weather outlook data found")

        total_time = (datetime.now() - start_time).total_seconds() * 1000
        external_logger.info(
            f"SELENIUM REQUEST SUCCESS - URL: {url} - "
            f"Total time: {total_time:.2f}ms - "
            f"Extracted {len(nhc_text)} text blocks"
        )

    except Exception as e:
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        external_logger.error(
            f"SELENIUM REQUEST ERROR - URL: {url} - "
            f"Error: {str(e)} - "
            f"Time: {total_time:.2f}ms"
        )
        nhc_text.append("Error extracting NHC data")
    finally:
        # Ensure driver is properly closed
        if driver:
            try:
                driver.quit()
            except Exception as e:
                external_logger.warning(f"SELENIUM CLEANUP WARNING - Error closing driver: {str(e)}")
    
    return nhc_text


# Global dictionaries to store images and descriptions
nws_image = {}
nws_description = {}


def append_datetime(input_string):
    """
    Appends the current datetime in yymmdd_hhmmss format to a string.
    
    Args:
        input_string (str): The base string to append datetime to
        
    Returns:
        str: String with datetime appended
    """
    short_fmt = "_%m%d_%H%M"
    now = datetime.now()
    datetime_string = now.strftime(short_fmt)
    return input_string + datetime_string


def retrieve_nws_info():
    """
    Populate the dictionaries with the images and descriptions from the NWS pages.
    """
    for e in NWS_FORECAST_OFFICES:
        page_url = f"{NWS_BASE_URL}/{NWS_FORECAST_OFFICES[e]}/"
        nws_response = request_page(page_url)
        
        nws_info = extract_nws_info(nws_response)
        nws_description[e] = nws_info["description"] 
        image_url = nws_info["image_url"] 
        nws_image[e] = get_image(image_url)


def generate_sitrep_document(label1_value):
    """
    Generate the sitrep document and return the file path.
    
    Args:
        label1_value (str): Optional label to append to the document title
        
    Returns:
        str: Path to the generated temporary document file
        
    Raises:
        Exception: If document generation fails
    """
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx', prefix='sitrep_')
    temp_file.close()
    
    try:
        # Prepare document
        document = Document()
        font = document.styles['Normal'].font
        font.name = 'Calibri'
        font.size = Pt(12)
        
        # Add custom label if provided
        title = TITLE 
        if label1_value:
            title = f'{title} - {label1_value}'
        
        heading = document.add_heading(title, 0)

        # NWS offices
        retrieve_nws_info()
        for ofc in NWS_FORECAST_OFFICES:
            document.add_heading(ofc, level=2)
            if ofc in nws_image and nws_image[ofc]:
                try:
                    document.add_picture(nws_image[ofc], width=Inches(5.5))
                except Exception:
                    pass

            if ofc in nws_description:
                document.add_paragraph(nws_description[ofc].strip())
            document.add_section(WD_SECTION.NEW_PAGE)

        # NHC 7-day forecast
        nhc_img = get_image(NHC_7DAY_IMG_URL)
        document.add_heading('Seven Day Forecast', level=2)
        if nhc_img:
            try:
                document.add_picture(nhc_img, width=Inches(5.5))
            except Exception:
                pass
        
        nhc_texts = extract_text_arrays_from_url(NHC_URL)
        for txt in nhc_texts:
            document.add_paragraph(txt)
        document.add_section(WD_SECTION.NEW_PAGE)

        # Fire Risk
        fire_risk_img = get_image(FIRE_DANGER_IMAGE_URL)
        document.add_heading('Fire Danger Maps', level=2)
        if fire_risk_img:
            try:
                document.add_picture(fire_risk_img, width=Inches(4.0))
            except Exception:
                pass

        # Save document
        document.save(temp_file.name)
        
        # Verify the file was created and has content
        if os.path.exists(temp_file.name):
            file_size = os.path.getsize(temp_file.name)
            if file_size > 0:
                return temp_file.name
            else:
                raise Exception("Document file is empty after saving")
        else:
            raise Exception("Document file was not created")
        
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise e


def generate_sitrep_document_with_progress(label1_value, task_id):
    """
    Generate the sitrep document with real-time progress updates.
    
    Args:
        label1_value (str): Optional label to append to the document title
        task_id (str): Unique task identifier for progress tracking
        
    Yields:
        dict: Progress updates with status, progress percentage, and messages
        
    Raises:
        Exception: If document generation fails
    """
    import re
    
    completed_steps = []
    
    # Local dictionaries to avoid global state issues
    local_nws_image = {}
    local_nws_description = {}
    
    try:
        # Step 1: Initialize document
        yield {
            'status': 'in_progress',
            'progress': 5,
            'message': 'Initializing document...',
            'current_step': 1,
            'completed_steps': completed_steps
        }
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx', prefix='sitrep_')
        temp_file.close()
        
        # Prepare document
        document = Document()
        font = document.styles['Normal'].font
        font.name = 'Calibri'
        font.size = Pt(12)
        
        # Add custom label if provided
        title = TITLE 
        if label1_value:
            title = f'{title} - {label1_value}'
        
        heading = document.add_heading(title, 0)
        completed_steps.append(1)
        
        # Step 2-4: NWS offices (we'll do them individually for progress)
        office_names = list(NWS_FORECAST_OFFICES.keys())
        
        for i, office_name in enumerate(office_names):
            step_num = i + 2
            yield {
                'status': 'in_progress',
                'progress': 10 + (i * 15),
                'message': f'Fetching {office_name} data...',
                'current_step': step_num,
                'completed_steps': completed_steps
            }
            
            office_code = NWS_FORECAST_OFFICES[office_name]
            page_url = f"{NWS_BASE_URL}/{office_code}/"
            nws_response = request_page(page_url)
            
            nws_info = extract_nws_info(nws_response)
            local_nws_description[office_name] = nws_info["description"] 
            image_url = nws_info["image_url"] 
            local_nws_image[office_name] = get_image(image_url)
            
            # Add to document
            document.add_heading(office_name, level=2)
            if office_name in local_nws_image and local_nws_image[office_name]:
                try:
                    document.add_picture(local_nws_image[office_name], width=Inches(5.5))
                except Exception:
                    pass

            if office_name in local_nws_description:
                document.add_paragraph(local_nws_description[office_name].strip())
            document.add_section(WD_SECTION.NEW_PAGE)
            
            completed_steps.append(step_num)
        
        # Step 5: NHC 7-day forecast
        yield {
            'status': 'in_progress',
            'progress': 55,
            'message': 'Fetching NHC forecast data...',
            'current_step': 5,
            'completed_steps': completed_steps
        }
        
        nhc_img = get_image(NHC_7DAY_IMG_URL)
        document.add_heading('Seven Day Forecast', level=2)
        if nhc_img:
            try:
                document.add_picture(nhc_img, width=Inches(5.5))
            except Exception:
                pass
        
        nhc_texts = extract_text_arrays_from_url(NHC_URL)
        for txt in nhc_texts:
            document.add_paragraph(txt)
        document.add_section(WD_SECTION.NEW_PAGE)
        completed_steps.append(5)

        # Step 6: Fire Risk
        yield {
            'status': 'in_progress',
            'progress': 75,
            'message': 'Fetching fire danger maps...',
            'current_step': 6,
            'completed_steps': completed_steps
        }
        
        fire_risk_img = get_image(FIRE_DANGER_IMAGE_URL)
        document.add_heading('Fire Danger Maps', level=2)
        if fire_risk_img:
            try:
                document.add_picture(fire_risk_img, width=Inches(4.0))
            except Exception:
                pass
        completed_steps.append(6)

        # Step 7: Save document
        yield {
            'status': 'in_progress',
            'progress': 90,
            'message': 'Generating final document...',
            'current_step': 7,
            'completed_steps': completed_steps
        }
        
        document.save(temp_file.name)
        completed_steps.append(7)
        
        # Step 8: Finalize
        yield {
            'status': 'in_progress',
            'progress': 95,
            'message': 'Finalizing report...',
            'current_step': 8,
            'completed_steps': completed_steps
        }
        
        # Verify the file was created and has content
        if os.path.exists(temp_file.name):
            file_size = os.path.getsize(temp_file.name)
            if file_size > 0:
                # Create filename with timestamp
                base_filename = OUTPUT_FILE_NAME
                if label1_value:
                    # Replace spaces and special characters for filename
                    safe_label = re.sub(r'[^\w\-_]', '_', label1_value)
                    base_filename = f'{base_filename}_{safe_label}'
                
                filename = append_datetime(base_filename) + '.docx'
                completed_steps.append(8)
                
                # Final success
                yield {
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Report generated successfully!',
                    'current_step': None,
                    'completed_steps': completed_steps,
                    'file_path': temp_file.name,
                    'filename': filename
                }
            else:
                raise Exception("Document file is empty after saving")
        else:
            raise Exception("Document file was not created")
        
    except Exception as e:
        # Clean up temp file on error
        if 'temp_file' in locals() and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        
        yield {
            'status': 'error',
            'progress': 0,
            'message': f'Error generating report: {str(e)}',
            'error': str(e)
        }