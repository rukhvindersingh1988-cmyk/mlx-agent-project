import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class WebScraper:
    """
    A web scraper that fetches URLs and extracts links and page titles.
    
    Attributes:
        user_agent (str): User agent string for requests
        timeout (int): Request timeout in seconds
    """
    
    def __init__(self, user_agent=None, timeout=10):
        """
        Initialize the scraper with optional user agent and timeout.
        
        Args:
            user_agent (str, optional): Custom user agent string. Defaults to a common browser UA.
            timeout (int, optional): Request timeout in seconds. Defaults to 10.
        """
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.timeout = timeout
    
    def scrape_page(self, url):
        """
        Fetch a URL and extract all links and page title.
        
        Args:
            url (str): The URL to scrape
            
        Returns:
            dict: A dictionary containing:
                - 'url': The original URL
                - 'title': The page title
                - 'links': List of absolute URLs found on the page
                - 'status_code': HTTP status code
                
        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        headers = {'User-Agent': self.user_agent}
        
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract page title
            title = soup.title.string if soup.title else "No title found"
            
            # Extract all links and convert to absolute URLs
            links = []
            for link in soup.find_all('a', href=True):
                absolute_url = urljoin(url, link['href'])
                if absolute_url.startswith(('http://', 'https://')):
                    links.append(absolute_url)
            
            return {
                'url': url,
                'title': title,
                'links': links,
                'status_code': response.status_code
            }
            
        except requests.exceptions.RequestException as e:
            raise e
            
    def scrape_multiple(self, urls):
        """
        Scrape multiple URLs and return a list of results.
        
        Args:
            urls (list): List of URLs to scrape
            
        Returns:
            list: List of dictionaries with scrape results
        """
        results = []
        for url in urls:
            try:
                results.append(self.scrape_page(url))
            except requests.exceptions.RequestException:
                results.append({
                    'url': url,
                    'title': "Failed to fetch",
                    'links': [],
                    'status_code': None
                })
        return results