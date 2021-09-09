### Background ###
This repo is for a web scraper to get the document history for any given PIN in Chicago.

To run this you'll need a [Selenium](https://selenium-python.readthedocs.io/installation.html) webdriver. I'm using Firefox and installed using brew.

Selenium's not really supposed to be used as a scraper since it's slow and inefficient, but this website had a lot of JavaScript so I caved in and went with the hacky solution.

### Installation ###
1. Install Selenium webdriver
2. Make a virtual environment with `pip3 -m venv env`
3. Activate your environment with `source env/bin/activate`
4. Install requirements with `pip3 install -r requirements.txt`
5. Run the scraper with `python3 scrape.py`

###### Other Files ######
*douglas_pins.csv* is a list of all the PIN within the Chicago Community Area labeled Douglas

*results.csv* is a list of the results of one PIN from the Douglas neighborhood

*scraper_log.py* is a module to make logs for extended scraping if the data has legs