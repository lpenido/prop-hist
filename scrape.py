import os
import csv
import time
import logging 

# Environment
from dotenv import load_dotenv
load_dotenv()

# General utility 
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys

# For safe loading the pages 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

# HTML Parsing
from bs4 import BeautifulSoup

url = "http://162.217.184.82/i2/default.aspx?AspxAutoDetectCookieSupport=1" # url to hit
s_delay, m_delay, l_delay = 3, 5, 10 # delays to be used

# Pages that will be visited 
result_page = {
    "table": '/html/body/form/div[5]/div[31]/div[1]/div[2]/table/tbody/tr[1]/td/div/div[2]/table/tbody'
}

home_page = {
    "home_btn": '//*[@id="Navigator1_SearchHome1"]',
    "search_btn": '//*[@id="SearchFormEx1_btnSearch"]',
    "s0": '//*[@id="SearchFormEx1_PINTextBox0"]',
    "s1": '//*[@id="SearchFormEx1_PINTextBox1"]',
    "s2": '//*[@id="SearchFormEx1_PINTextBox2"]',
    "s3": '//*[@id="SearchFormEx1_PINTextBox3"]',
    "s4": '//*[@id="SearchFormEx1_PINTextBox4"]'
}

def is_page_valid(driver, page_info):
    """
    Validator function. Checks to make sure elements that will be used
    later on are present on the page.

    :driver: selenium webdriver object 
    :page_info: dict of elements to validate are present on page
    :returns: bool
    """
    for key in page_info:
        element = page_info[key]
        try:
            que = EC.presence_of_element_located((By.XPATH, element))
            WebDriverWait(driver, m_delay).until(que)
        except NoSuchElementException:
            logger.warning(f'{key} NOT found on page')
            return False
    logger.info("Page is valid")
    return True

def search_pin(driver, pin):
    """
    Searches the given pin on the home page

    :driver: selenium webdriver object
    :pin: string, unique parcel IDs to search records for
    """
    search_box = (
        home_page["s0"], 
        home_page["s1"],
        home_page["s2"],
        home_page["s3"],
        home_page["s4"],
    )
    split_pin = pin.split("-")
    zipped_list = zip(split_pin, search_box)
    for pin_part, search_box in zipped_list:
        element = driver.find_element_by_xpath(search_box)
        element.clear()
        element.send_keys(pin_part)
    
    driver.find_element_by_xpath(home_page["search_btn"]).click()

def is_next_button_present(driver):
    """
    Validator function. In case the table doesn't have a next button.

    :driver: selenium webdriver object
    :returns: bool
    """
    try:
        next_btn = '//*[@id="DocList1_LinkButtonNext"]'
        driver.find_element_by_xpath(next_btn)
        logger.info("Next button was found")
        return True
    except NoSuchElementException:
        logger.warning("Next button was NOT found")
        return False

def go_to_next_page(driver):
    """Helper function to navigate long histories"""
    next_btn = '//*[@id="DocList1_LinkButtonNext"]'
    driver.find_element_by_xpath(next_btn).click()
    
def parse_table_row(table_row_html):
    """
    Used to transform the raw html of a table row into a dictionary
    for writing to csv/db

    :table_row_html: string of raw html
    :returns: dict of result table row
    """
    row = table_row_html.find_all("td")
    return {
        "recorded_date": row[1].text,
        "pin": row[2].text,
        "type_desc": row[3].text,
        "doc_num": row[4].text,
        "first_grantor": row[5].text,
        "first_grantee": row[6].text,
        "first_prior_doc_num": row[7].text
    }

def scrape_result_table(driver):
    """
    Takes the raw html of the entire page, locates the result table, and
    iterates through each row to parse

    :driver: selenium webdriver object 
    :results: list of dictionaries, each is a result table row
    """
    # Gets the current page's html in one string and parses in bs4
    source = driver.page_source 
    soup = BeautifulSoup(source, 'html.parser')

    # There's 45 tables on each page, #40 is the result table
    tables = soup.find_all('table')
    result_table_rows = tables[40].find_all("tr")

    # By default there's 24 rows per table, only 20 have results
    # Assumes the last row is the next button
    results = []
    for row in result_table_rows[2:-2]:
        row_dict = parse_table_row(row)
        results.append(row_dict)

    return results

def save_scrape_to_csv(results):
    """
    Saves the results to a hardcoded outfile for now. Uses the 'a' flag
    for 'append' instead of 'w' for 'writing' to not overwrite other pins

    TODO: Add a sqlite3 db if the prelim data has legs

    :results: list of dicts
    """
    output_filename = "results.csv"
    with open(output_filename, 'a') as f:
        dict_writer = csv.DictWriter(f, fieldnames=results[0].keys())
        dict_writer.writeheader()
        dict_writer.writerows(results)

def return_to_home_page(driver):
    """Helper function to restart the loop for the next search"""
    home_btn = home_page["home_btn"]
    driver.find_element_by_xpath(home_btn).click()

def search_and_save_pin(driver, pin):
    """
    Searches the pin, if there are multiple pages, it will scrape until no
    next button is found, then save to csv and return to the home page to 
    begin the next pin

    :driver: selenium webdriver object
    :pin: string, unique parcel IDs to search records for
    """
    try:
        assert is_page_valid(driver, home_page) == True

        print("Searching:", pin)
        search_pin(driver, pin)
        print("Searched:", pin)

        # The case of n next buttons
        results = []
        if is_page_valid(driver, result_page) and is_next_button_present(driver):
            while is_next_button_present(driver):
                result = scrape_result_table(driver)
                results += result
                go_to_next_page(driver)
                time.sleep(m_delay)

        # The case of no next buttons/last page 
        if is_page_valid(driver, result_page) and not is_next_button_present(driver):
            result = scrape_result_table(driver)
            results += result
        
        save_scrape_to_csv(results)
        return_to_home_page(driver)
    
    except AssertionError:
        print("Home page was not valid!")

def main(pins):
    """
    Starts the scraper, scraping each pin in the list, and makes sure
    it terminates safely

    :pins: list of strings, of unique parcel IDs to search records for
    """
    # Selenium init
    logger.info("Starting driver.")
    options = Options()
    options.add_argument("--headless") # Comment out to see the browser
    driver = webdriver.Firefox(options=options)

    try:
        driver.get(url)

        time.sleep(m_delay)

        for pin in pins:
            print("Starting:", pin)
            search_and_save_pin(driver, pin)
            print("Finished:", pin)
                
        time.sleep(m_delay)

    finally:
        logger.info("Closing driver...")
        driver.close()
        driver.quit()
        logger.info("Drivers Closed.")

if __name__ == "__main__":

    # Make sure logs will log
    if not os.path.exists('logs'):
        os.mkdir('logs')
 
    # TODO: Finish logging
    logger = logging.getLogger('scraper_log')
    test_pin = [
        "17-34-326-006-0000",
    ]

    start = time.perf_counter()
    main(test_pin)
    end = time.perf_counter()
    print(f"Scraped one PIN in {end:0.4f} seconds") # To get an estimate for how long a whole nbhd would take
