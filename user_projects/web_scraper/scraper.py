import requests
from bs4 import BeautifulSoup

class WebScraper:
    def __init__(self, url):
        self.url = url
        self.response = None
        self.soup = None
        self.links = []
        self.title = None

    def fetch(self):
        try:
            self.response = requests.get(self.url)
            self.response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {self.url}: {e}")
            return None

    def parse(self):
        if self.response is None:
            return None
        self.soup = BeautifulSoup(self.response.text, 'html.parser')
        self.title = self.soup.find('title').text if self.soup.find('title') else None
        for link in self.soup.find_all('a'):
            href = link.get('href')
            if href and href.startswith('http'):
                self.links.append(href)

    def scrape(self):
        self.fetch()
        self.parse()
        return {
            'url': self.url,
            'title': self.title,
            'links': self.links
        }
