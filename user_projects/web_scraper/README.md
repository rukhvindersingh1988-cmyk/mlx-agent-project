# WebScraper Package

A simple Python package for web scraping using requests and BeautifulSoup.

## Installation
```bash
pip install requests beautifulsoup4
```

## Usage
```python
from webscraper import WebScraper

# Initialize scraper
scraper = WebScraper()

# Scrape a webpage
result = scraper.scrape('https://example.com')
print(result)
```

## API Documentation

### WebScraper.scrape(url: str) -> dict
Scrapes the given URL and returns structured data.

Parameters:
- url (str): The URL to scrape

Returns:
- dict: Contains:
  - 'status': HTTP status code
  - 'title': Page title
  - 'links': List of found URLs
  - 'text': Main page text content
