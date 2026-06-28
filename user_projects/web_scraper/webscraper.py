import requests
from bs4 import BeautifulSoup

class WebScraper:
    def scrape(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise e
