# Configuration file for ARC SFL Region Weather Sitrep Generator
PORT_NUMBER = 8080

# NWS (National Weather Service) Configuration
NWS_FORECAST_OFFICES = {
    'NWS Miami Office': 'mfl',
    'NWS Tampa Office': 'tbw',
    'NWS Melbourne Office': 'mlb'
}

NWS_BASE_URL = 'https://weather.gov'
NWS_DESCRIPTION_SELECTOR = '.graphicast > div.description'

# NHC (National Hurricane Center) Configuration
NHC_URL = 'https://www.nhc.noaa.gov/'
NHC_7DAY_IMG_URL = 'https://www.nhc.noaa.gov/xgtwo/two_atl_7d0.png'

# Fire Danger Configuration
FIRE_DANGER_IMAGE_URL = 'https://weather.fdacs.gov/FDI/images/FL-latest-fcst.png'

# Application Configuration
TITLE = 'SFL Region Weather Sitrep worksheet'
NO_IMAGE = 'IMAGE NOT AVAILABLE'
NO_CAPTION = '*** CAPTION NOT PROVIDED FOR THIS IMAGE ***'
OUTPUT_FILE_NAME = 'sitrep_workfile'

# How long to wait before closing the Success message (in msecs.)
DELAY_MS = 10000

