from setuptools import setup, find_packages

setup(
    name='webscraper',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'requests>=2.25.1',
        'beautifulsoup4>=4.9.3'
    ],
    author='Your Name',
    author_email='your.email@example.com',
    description='A simple web scraping package',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/webscraper'
)