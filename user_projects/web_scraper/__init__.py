import requests
from bs4 import BeautifulSoup

class WebScraper:
    """
    A web scraping utility class
    """
    def scrape(self, url):
        """
        Scrapes the given URL and returns structured data
        
        Args:
            url (str): The URL to scrape
            
        Returns:
            dict: Contains status code, title, links and text content
        """
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return {
                'status': response.status_code,
                'title': soup.title.string if soup.title else None,
                'links': [a['href'] for a in soup.find_all('a', href=True)],
                'text': soup.get_text()
            }
        except Exception as e:
            return {'error': str(e)}