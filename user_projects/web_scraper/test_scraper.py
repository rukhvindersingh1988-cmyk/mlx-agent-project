import pytest
from unittest.mock import patch, Mock
from web_scraper.scraper import WebScraper


def mock_response(status_code=200, content=b''):
    mock = Mock()
    mock.status_code = status_code
    mock.content = content
    return mock

@patch('requests.get')
def test_scrape(mock_get):
    # Arrange
    mock_get.return_value = mock_response(
        content=b'<html><head><title>Test Page</title></head><body><a href="https://example.com">Link</a></body></html>'
    )
    scraper = WebScraper()

    # Act
    result = scraper.scrape('https://example.com')

    # Assert
    assert result == {
        'title': 'Test Page',
        'links': ['https://example.com']
    }

@patch('requests.get')
def test_scrape_no_links(mock_get):
    # Arrange
    mock_get.return_value = mock_response(
        content=b'<html><head><title>Test Page</title></head><body></body></html>'
    )
    scraper = WebScraper()

    # Act
    result = scraper.scrape('https://example.com')

    # Assert
    assert result == {
        'title': 'Test Page',
        'links': []
    }

@patch('requests.get')
def test_scrape_404(mock_get):
    # Arrange
    mock_get.return_value = mock_response(status_code=404)
    scraper = WebScraper()

    # Act & Assert
    with pytest.raises(Exception, match='Failed to scrape'):
        scraper.scrape('https://example.com')