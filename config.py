# Configuration file for ARC SFL Region Weather Sitrep Generator
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

PORT_NUMBER = 8080

# Firecrawl Configuration
FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY', '')

# NWS (National Weather Service) Configuration
NWS_FORECAST_OFFICES = {
    'MIAMI-DADE, BROWARD, PALM BEACH, COLLIER (NWS:MFL)': 'mfl',
    'LEE, CHARLOTTE, SARASOTA, HIGHLANDS, HARDEE, POLK (NWS:TBW)': 'tbw',
    'MARTIN, ST LUCIE, INDIAN RIVER, OKEECHOBEE (NWS:MLB)': 'mlb'
}

NWS_BASE_URL = 'https://weather.gov'
NWS_DESCRIPTION_SELECTOR = '.graphicast > div.description'

# NHC (National Hurricane Center) Configuration
NHC_URL = 'https://www.nhc.noaa.gov/'
NHC_7DAY_IMG_URL = 'https://www.nhc.noaa.gov/xgtwo/two_atl_7d0.png'

# Fire Danger Configuration
FIRE_DANGER_URL = 'https://weather.fdacs.gov/FDI'
FIRE_DANGER_IMAGE_URL = f"{FIRE_DANGER_URL}/images/FL-latest-fcst.png"

# Application Configuration
TITLE = 'SFL Region Weather Sitrep worksheet'
NO_IMAGE = 'IMAGE NOT AVAILABLE'
NO_CAPTION = '*** CAPTION NOT PROVIDED FOR THIS IMAGE ***'
OUTPUT_FILE_NAME = 'sitrep_workfile'

# Logging Configuration
LOG_LEVEL = 'INFO'
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
SLOW_REQUEST_THRESHOLD = 5000  # milliseconds
