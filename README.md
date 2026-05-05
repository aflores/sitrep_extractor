# ARC SFL Region Weather Sitrep Generator

A web application that generates Weather Situation Reports (Sitreps) for the American Red Cross South Florida Region.

## Features

- **NWS Reports**: Automatically fetches current weather reports from Miami, Tampa, and Melbourne National Weather Service offices
- **NHC Seven-Day Forecast**: Includes the latest National Hurricane Center 7-day graphical tropical weather outlook
- **Fire Danger Maps**: Incorporates Florida Department of Agriculture fire danger maps
- **Custom Labels**: Add custom labels to reports for special events or specific purposes
- **Direct Download**: Downloads the generated Word document directly to your computer

## Components Included in Each Report

1. **NWS Office Reports**:
   - NWS Miami Office (MFL)
   - NWS Tampa Office (TBW)
   - NWS Melbourne Office (MLB)
   - Each includes the latest forecast image and description

2. **NHC Seven-Day Graphical Tropical Weather Outlook**:
   - Latest 7-day forecast image
   - Detailed text descriptions of tropical weather systems

3. **Fire Danger Maps**:
   - Current Florida fire danger forecast map

## Installation

1. **Clone or download the project files**

2. **Set up configuration**:
   - Edit `config.py` to customize URLs and settings if needed
   - Set your Firecrawl secret as an environment variable:
   ```bash
   export FIRECRAWL_API_KEY="fc-your-key"
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. **Start the Flask server**:
   ```bash
   python app.py
   ```

2. **Open your web browser** and navigate to:
   ```
   http://localhost:5000
   ```

3. **Generate a report**:
   - Enter an optional custom label for your report
   - Click "Generate Sitrep Report"
   - Wait for the report to be generated (this may take a few minutes)
   - The Word document will automatically download

## Usage Notes

- **Report Generation Time**: The process typically takes 2-5 minutes depending on network speed and website response times
- **File Format**: Reports are generated as Microsoft Word (.docx) files
- **File Naming**: Files are automatically named with timestamps (e.g., `sitrep_workfile_1029_1430.docx`)
- **Custom Labels**: If you enter a custom label, it will be included in both the document title and filename

## Technical Requirements

- Python 3.7+
- Internet connection (for fetching weather data)

## Troubleshooting

- **Missing Firecrawl API Key**: Ensure `FIRECRAWL_API_KEY` is set in your environment before running the app
- **Network Timeouts**: Some weather websites may be slow to respond; the application will retry or use placeholder content
- **Memory Usage**: The application processes images and web content, so ensure adequate system memory

## Original Jupyter Notebook

This Flask application is based on the original Jupyter notebook `sitrep_extractor.ipynb`, which contains the core logic for data extraction and document generation.

## Project Structure

```
sitrep_extractor/
├── app.py                    # Flask web application
├── config.py                 # Configuration settings
├── requirements.txt          # Python dependencies
├── templates/
│   └── index.html           # Web interface template
├── sitrep_extractor.ipynb   # Original Jupyter notebook
├── drafts/                  # Directory for draft files (if needed)
└── .gitignore              # Git ignore rules
```

## Configuration

The application uses a `config.py` file to store all URLs and settings. You can customize:

- **NWS Office URLs**: Add or modify National Weather Service office endpoints
- **Data Source URLs**: Update URLs for NHC forecasts and fire danger maps
- **CSS Selectors**: Modify HTML selectors for data extraction
- **Output Settings**: Change default filenames and formats

Key configuration options in `config.py`:
- `NWS_FORECAST_OFFICES`: Dictionary of NWS offices and their codes
- `NWS_BASE_URL`: Base URL for National Weather Service
- `NHC_URL`: National Hurricane Center URL
- `FIRE_DANGER_IMAGE_URL`: Florida fire danger map URL


Run locally with:
conda run -p /Users/aflores/miniconda3 --no-capture-output python app.py
