import os
import csv
import time
import logging
import sqlite3
import random

import pandas as pd

# Environment
from dotenv import load_dotenv
load_dotenv()

# General utility 
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys

# For safe loading the pages 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# HTML Parsing
from bs4 import BeautifulSoup

# Config vars
url = "http://162.217.184.82/i2/default.aspx?AspxAutoDetectCookieSupport=1" # url to hit
s_delay, m_delay, l_delay = 3, 5, 10 # delays to be used

# Pages that will be visited 
result_page = {
    "table": '/html/body/form/div[5]/div[31]/div[1]/div[2]/table/tbody/tr[1]/td/div/div[2]/table/tbody'
}

home_page = {
    "home_btn": '//*[@id="Navigator1_SearchHome1"]',
    "search_btn": '//*[@id="SearchFormEx1_btnSearch"]',
    "reset": '//*[@id="SearchFormEx1_BtnReset"]',
    "s0": '//*[@id="SearchFormEx1_PINTextBox0"]', 
    "s1": '//*[@id="SearchFormEx1_PINTextBox1"]',
    "s2": '//*[@id="SearchFormEx1_PINTextBox2"]',
    "s3": '//*[@id="SearchFormEx1_PINTextBox3"]',
    "s4": '//*[@id="SearchFormEx1_PINTextBox4"]',
}

def rand_rest():
    time.sleep(random.randint(0, 3))

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
            WebDriverWait(driver, l_delay).until(que)
        
        except TimeoutException:
            logger.warning(f"Page timed out on {key}")
            return False

        except NoSuchElementException:
            logger.warning(f'{key} NOT found on page')
            return False

    logger.info("Page is valid")
    return True

def smart_action(driver, x_path, delay):
    """Wrapper function to wait for the element to appear in the DOM"""
    que = EC.presence_of_element_located((By.XPATH, x_path))
    element = WebDriverWait(driver, delay).until(que)
    return element

def zero_hits(driver):
    """Helper function to deal with 0 hits pop up window"""
    zero_hits = '//*[@id="MessageBoxCtrl1_buttonmbatCLIENTOK"]'
    element = smart_action(driver, zero_hits, l_delay)
    element.click()

def wait_until_unblocked(driver):
    que = EC.invisibility_of_element_located((By.ID, 'MessageBoxCtrl1_ScreenBlocker'))
    element = WebDriverWait(driver, l_delay).until(que)
    return element

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
        try:
            element = smart_action(driver, search_box, m_delay)
            element.clear() # some reason this raised stale element errors
            element.send_keys(pin_part)

        # If it's state, try redefining it and running 
        except StaleElementReferenceException:
            text_box = smart_action(driver, search_box, l_delay)
            text_box.send_keys(pin_part)

        except NoSuchElementException:
            logger.warning(f'{pin_part} failed to search')

    element = smart_action(driver, home_page["search_btn"], l_delay)
    rand_rest()
    try:
        element.click()
    
    # If it's state, try redefining it and running 
    except StaleElementReferenceException:
        button = smart_action(driver, home_page["search_btn"], l_delay)
        button.click()

    # If there's a pop-up, log it and freeze to take a look
    except ElementClickInterceptedException:
        try:
            wait_until_unblocked(driver)
            zero_hits(driver)

        except Exception as e:
            print(e)
            breakpoint()
    

def is_next_button_present(driver):
    """
    Validator function. To find end of tables and in case the table doesn't
    have a next button.

    :driver: selenium webdriver object
    :returns: bool
    """
    try:
        next_btn = '//*[@id="DocList1_LinkButtonNext"]'
        driver.find_element_by_xpath(next_btn)
        logger.info("Next button was found")
        return True
    except NoSuchElementException:
        logger.info("No next button found. End of table.")
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

def is_duplicate(conn, record):
    """
    To check if the record about to be added exits. #NoDupes
    """
    sql = """
    SELECT * FROM records
    WHERE 
        recorded_date=? AND 
        pin=? AND
        type_desc=? AND
        doc_num=? AND
        first_grantor=? AND
        first_grantee=? AND
        first_prior_doc_num=?;
    """
    record_to_search = (
        record["recorded_date"],
        record["pin"],
        record["type_desc"],
        record["doc_num"],
        record["first_grantor"],
        record["first_grantee"],
        record["first_prior_doc_num"]
    )

    # Connection should still be open since it's inside main()
    cur = conn.cursor()
    searched_record = cur.execute(sql, record_to_search)
    searched_record = searched_record.fetchone()

    if searched_record == None:
        return False
    else:
        return True

def insert_record_to_db(conn, record):
    """
    To insert a singular row into the db

    """
    if is_duplicate(conn, record):
        logger.info(f"Duplicated Record: {record}")
    else:
        # Setting up query
        sql = """
        INSERT INTO records (recorded_date, pin, type_desc, doc_num, first_grantor, first_grantee, first_prior_doc_num)
        VALUES(?,?,?,?,?,?,?);
        """
        record_to_add = (
            record["recorded_date"],
            record["pin"],
            record["type_desc"],
            record["doc_num"],
            record["first_grantor"],
            record["first_grantee"],
            record["first_prior_doc_num"]
        )
        
        # Adding to db
        cur = conn.cursor()
        cur.execute(sql, record_to_add)
        conn.commit()

def save_scrape_to_db(conn, results):
    """
    To add a list of results to the db

    :results: list of dicts
    """
    for result in results:
        insert_record_to_db(conn, result)

def save_scrape_to_csv(results, output_filename="results.csv"):
    """
    Saves the results to a hardcoded outfile for now. Uses the 'a' flag
    for 'append' instead of 'w' for 'writing' to not overwrite other pins

    Might contain duplicates. We'll fix it in post...

    :results: list of dicts
    """
    fieldnames = ["recorded_date", "pin", "type_desc", "doc_num", "first_grantor", "first_grantee", "first_prior_doc_num"]
    with open(output_filename, 'a') as f:
        dict_writer = csv.DictWriter(f, fieldnames=fieldnames)
        dict_writer.writerows(results)

def return_to_home_page(driver):
    """Helper function to restart the loop for the next search"""
    home_btn = home_page["home_btn"]
    try:
        driver.find_element_by_xpath(home_btn).click()
    except ElementClickInterceptedException:
        wait_until_unblocked(driver)
        driver.find_element_by_xpath(home_btn).click()

def search_and_save_pin(driver, pin, conn):
    """
    Searches the pin, if there are multiple pages, it will scrape until no
    next button is found, then save to csv and return to the home page to 
    begin the next pin

    :driver: selenium webdriver object
    :pin: string, unique parcel IDs to search records for
    :conn: sqlite3 connection object
    """
    try:
        assert is_page_valid(driver, home_page) == True

        logger.info(f"{pin}: Searching")
        search_pin(driver, pin)
        logger.info(f"{pin}: Searched")

        # The case of n next buttons
        results = []
        logger.info(f"{pin}: Scraping")
        if is_page_valid(driver, result_page) and is_next_button_present(driver):
            while is_next_button_present(driver):
                result = scrape_result_table(driver)
                results += result
                go_to_next_page(driver)
                rand_rest()

        # The case of no next buttons/last page 
        if is_page_valid(driver, result_page) and not is_next_button_present(driver):
            result = scrape_result_table(driver)
            results += result
        
        logger.info(f"{pin}: Scraped")
        
        # Gotta get the db and the hard copy
        logger.info(f"{pin}: Saving")
        save_scrape_to_db(conn, results)
        save_scrape_to_csv(results)
        logger.info(f"{pin}: Saved")

        return_to_home_page(driver)
    
    except AssertionError:
        print("Home page was not valid!")

def main(pins):
    """
    Starts the scraper, scraping each pin in the list, and makes sure
    it terminates safely

    :pins: list of strings, of unique parcel IDs to search records for
    """
    # Quick type check
    assert isinstance(pins, list) == True

    # Selenium init
    logger.info("Starting driver.")
    options = Options()
    # options.add_argument("--headless") # Comment out to see the browser

    driver = webdriver.Firefox(options=options)

    logger.info("Opening connection.")
    conn = sqlite3.connect(db_file)

    try:

        rand_rest()

        driver.get(url)

        for pin in pins:

            logger.info(f"{pin}: Starting")

            # General try/except in case of breakage, to keep on keeping on
            try:
                search_and_save_pin(driver, pin, conn)
                logger.info(f"{pin}: Finished")

            except:
                logging.exception(f"Error occured on {pin}")
                logging.info("Moving on...")
                pass 
                
        rand_rest()

    finally:
        logger.info("Closing driver...")
        driver.close()
        driver.quit()
        logger.info("Drivers Closed.")

        logger.info("Closing connection...")
        conn.close()
        logger.info("Connection Closed.")

if __name__ == "__main__":

    # Make sure csv is available to append
    if not os.path.exists("results.csv"):
        output_filename = "results.csv"
        fieldnames = ["recorded_date", "pin", "type_desc", "doc_num", "first_grantor", "first_grantee", "first_prior_doc_num"]
        with open(output_filename, 'w') as f:
            dict_writer = csv.DictWriter(f, fieldnames=fieldnames)
            dict_writer.writeheader()

    # Make sure db exits
    db_file = os.environ.get("DB")
    if not os.path.exists(db_file):
        sql = """
        CREATE TABLE IF NOT EXISTS records (
            id integer PRIMARY KEY,
            recorded_date text NOT NULL,
            pin text,
            type_desc text NOT NULL,
            doc_num text NOT NULL,
            first_grantor text NOT NULL,
            first_grantee text NOT NULL,
            first_prior_doc_num text NOT NULL
        );"""
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute(sql)
        conn.commit()
        conn.close()

    # Make sure logs will log
    if not os.path.exists('logs'):
        os.mkdir('logs')
 
    # File logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler('./logs/scraper.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stream logging 
    streamer = logging.StreamHandler()
    streamer.setLevel(logging.DEBUG)
    streamer.setFormatter(formatter)
    logger.addHandler(streamer)

    pins = pd.read_csv("douglas_pins.csv")["pin"].to_list()
    test_pins = pins[:50] 

    start = time.perf_counter()
    main(test_pins)
    end = time.perf_counter()
    print(f"Scraped {len(test_pins)} PIN(s) in {end:0.4f} seconds") # To get an estimate for how long a whole nbhd would take
