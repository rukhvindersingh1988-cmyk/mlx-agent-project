# webscraper

A Python package for web scraping.

## Description
webscraper is a simple and easy-to-use package for scraping websites. It uses requests and beautifulsoup4 under the hood.

## Install Instructions
To install webscraper, run the following command:
```bash
pip install requests beautifulsoup4
```
And then install the package itself using pip (once it's available).

## Usage Example
```python
from webscraper import WebScraper

scraper = WebScraper()
result = scraper.scrape('https://www.example.com')
print(result)
```
## API Docs
### WebScraper.scrape()
#### Description
Scrape a website and return the HTML content.
#### Parameters
* `url` (str): The URL of the website to scrape.
#### Returns
* `str`: The HTML content of the website.
#### Raises
* `requests.RequestException`: If there is an error with the request.
