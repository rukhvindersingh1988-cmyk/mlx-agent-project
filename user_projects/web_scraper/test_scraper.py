import pytest
from unittest.mock import patch
from your_module import WebScraper  # replace 'your_module' with the actual module name
import requests

@pytest.fixture
def test_scraper():
    return WebScraper()

@patch('requests.get')
def test_scrape(test_get, test_scraper):
    test_get.return_value.text = '<html><head><title>Test Title</title></head><body><a href="https://www.test.com">Test Link</a></body></html>'
    result = test_scraper.scrape('https://www.test.com')
    assert result['title'] == 'Test Title'
    assert 'https://www.test.com' in result['links']

@patch('requests.get')
def test_scrape_empty(test_get, test_scraper):
    test_get.return_value.text = ''
    result = test_scraper.scrape('https://www.test.com')
    assert result['title'] == ''
    assert result['links'] == []

@patch('requests.get')
def test_scrape_exception(test_get, test_scraper):
    test_get.side_effect = requests.exceptions.RequestException
    with pytest.raises(Exception):
        test_scraper.scrape('https://www.test.com')