"""
Utility functions for web scraping and data extraction.
Contains functions related to HTTP requests, BeautifulSoup parsing, and data processing.
"""

import requests
import io
import re
import tempfile
import os
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
)


def request_page(url):
    """
    Fetch a page and return the text in the response.
    
    Args:
        url (str): The URL to fetch
        
    Returns:
        str or None: The response text if successful, None if there was an error
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException:
        return None
    except Exception:
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
    Fetch an image and return it as stream.
    
    Args:
        img_url (str): URL of the image to fetch
        
    Returns:
        io.BytesIO: Image stream
    """
    try:
        if not img_url:
            return show_image_error()
        
        img_response = requests.get(img_url)
        img_response.raise_for_status()
        image_stream = io.BytesIO(img_response.content)
        image_stream.seek(0)
        return image_stream
    except Exception:
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
    try:
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
        driver.quit()

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')

        # Find all <script> tags
        script_tags = soup.find_all('script')

        # Regex pattern to find arrays named 'Text'
        pattern = r'Text\[\d+\]\s*=\s*\[([^\]]*)\]'

        found_arrays = []
        for script in script_tags:
            if script.string:
                matches = re.finditer(pattern, script.string, re.MULTILINE)
                found_arrays.extend([match.group(1).strip() for match in matches])

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

    except Exception:
        nhc_text.append("Error extracting NHC data")
    
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