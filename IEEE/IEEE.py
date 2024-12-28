from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import json
import logging
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime
import os
import re
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the WebDriver service
service = Service(executable_path="chromedriver-win64/chromedriver.exe")
logging.info("Starting the WebDriver")
driver = webdriver.Chrome(service=service)
# driver= webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get("https://ieeexplore.ieee.org")
logging.info(f"Page title: {driver.title}")

# Wait for the page to load fully
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'Typeahead-input')))

# Search for the keyword "data"
search = driver.find_element(By.CLASS_NAME, 'Typeahead-input')
search.send_keys("DevOps")
search.send_keys(Keys.RETURN)

# Wait for search results to load
WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "List-results-items")))


try:
    filter_section = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "filter-box-header"))
    )
    filter_section.click()

    # Select the Early Access Articles checkbox directly
    early_access_filter = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//label[@for='refinement-ContentType:Early Access Articles']/input"))
    )
    early_access_filter.click()
    logging.info("Selected 'Early Access Articles' filter")

    # Click the apply button after selecting the filter
    apply_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Apply')]")
    apply_button.click()
    logging.info("Applied filters")
    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "List-results-items")))  # Wait for results to update

except NoSuchElementException as e:
    logging.error(f"Error: {e}")
except TimeoutException:
    logging.error("Timed out while waiting for filter section")

# Data storage for articles
articles = []

def extract_issn(driver):
    """Extract only Electronic ISSN from the article's detail page."""
    issn = ""

    try:
        # Extract Electronic ISSN directly if available
        electronic_issn_element = driver.find_element(By.XPATH, "//strong[contains(text(), 'Electronic ISSN:')]/parent::div")
        issn = electronic_issn_element.text.split(":")[-1].strip().replace("-", "")
        logging.info(f"Electronic ISSN extracted: {issn}")
    except NoSuchElementException:
        logging.info("Electronic ISSN not found, checking for collapsible ISSN section.")

    try:
        # If the ISSN section is collapsible, expand it
        issn_toggle_button = driver.find_element(By.XPATH, "//h2[contains(text(), 'ISSN Information:')]")
        if "fa-angle-down" in issn_toggle_button.find_element(By.TAG_NAME, "i").get_attribute("class"):
            issn_toggle_button.click()
            time.sleep(2)
            logging.info("Clicked to expand the ISSN section.")

        # Extract Electronic ISSN from expanded section if present
        issn_elements = driver.find_elements(By.CSS_SELECTOR, "div.abstract-metadata-indent div")
        for element in issn_elements:
            if "Electronic ISSN:" in element.text:
                issn = element.text.split(":")[-1].strip().replace("-", "")

        logging.info(f"Final ISSN extracted: {issn}")
    except NoSuchElementException:
        logging.error("ISSN information not found.")
    
    return issn


def scrape_authors(driver):
    """Extract authors' names from the article's detail page."""
    authors = []  # Change to a list instead of a dict

    try:
        # Wait for the authors section to be clickable
        authors_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'authors-header'))
        )
        authors_button.click()  # Click to expand the authors section
        logging.info("Clicked to expand the authors section.")

        # Wait for the authors to load
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, 'authors-accordion-container'))
        )

        # Extract authors' names
        author_cards = driver.find_elements(By.CLASS_NAME, 'authors-accordion-container')
        for card in author_cards:
            name_element = card.find_element(By.TAG_NAME, 'a')  # Author's name link
            name = name_element.text
            authors.append(name)  # Append directly to the list
            logging.info(f"Author extracted: {name}")

    except NoSuchElementException:
        logging.error("Authors section not found or could not be expanded.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    logging.info(f"Authors data extracted: {authors}")
    return authors  # Return the list of authors


# Function to extract keywords
def scrape_keywords(driver):
    """Extract only IEEE keywords from the page."""
    keywords = []

    try:
        # Click the toggle button to expand the keywords section if it is collapsed
        toggle_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.accordion-link#keywords"))
        )
        toggle_button.click()  # Simulate the click to expand

        # Locate the container with the keywords
        keyword_section = driver.find_elements(By.CSS_SELECTOR, "li.doc-keywords-list-item")
        
        # Extract IEEE Keywords
        for section in keyword_section:
            header = section.find_element(By.TAG_NAME, 'strong').text
            if header == "IEEE Keywords":
                ieee_keywords_elements = section.find_elements(By.CSS_SELECTOR, "ul.List--inline li a")
                for keyword in ieee_keywords_elements:
                    keywords.append(keyword.text.strip())
        
        logging.info(f"Extracted IEEE Keywords: {keywords}")
        return keywords

    except NoSuchElementException:
        logging.error("IEEE Keywords not found.")
        return keywords
    except Exception as e:
        logging.error(f"Error extracting IEEE Keywords: {e}")
        return keywords


def scrape_title(driver):
    try:
        # Locate the title element on the article page
        title_element = driver.find_element(By.CSS_SELECTOR, "h1.document-title.text-2xl-md-lh span")
        return title_element.text
    except NoSuchElementException:
        logging.warning("Title not found")
        return "Title not found"

# Extract authors and affiliations
def scrape_authors_with_affiliations(driver):
    authors_with_affiliations = []  # List to store authors and their affiliations

    try:
        # Wait for the authors section to be visible
        authors_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'authors-header'))
        )

        # Extract the authors' data from the visible section
        authors = driver.find_elements(By.CLASS_NAME, "authors-accordion-container")

        for auth in authors:
            try:
                # Extract author name
                name_element = auth.find_element(By.TAG_NAME, 'a')
                author_name = name_element.text

                # Extract full affiliation details
                text_lines = auth.text.split('\n')
                if len(text_lines) > 1:  # Ensure text has at least two lines (name and affiliation)
                    affiliation_line = text_lines[1].replace("View Profile", "").strip()

                    # Identify university and country from the affiliation line
                    parts = affiliation_line.split(', ')
                    if len(parts) >= 2:
                        university = ", ".join(parts[:-1])  # All but last part for university
                        country = parts[-1].strip()         # Last part for country
                    else:
                        university = affiliation_line.strip()
                        country = ''  # Country might not always be present

                    # Append author and affiliation data to the list
                    authors_with_affiliations.append({
                        'author': author_name,
                        'university': university,
                        'country': country,
                        'location': affiliation_line
                    })
            except Exception as sub_e:
                logging.warning(f"Error processing individual author entry: {sub_e}")

        # Logging the results
        logging.info(f"Extracted Author Information: {authors_with_affiliations}")

        # Return the list of authors with affiliations
        return authors_with_affiliations

    except Exception as e:
        logging.error(f"Error extracting authors and affiliations: {e}")
        return []


    
def get_total_citations(driver):
    try:
        # Locate the element containing the citation count
        citation_count_element = driver.find_element(By.CSS_SELECTOR, "button.document-banner-metric .document-banner-metric-count")

        # Extract the citation count text and convert it to an integer
        citation_count = int(citation_count_element.text)
        return citation_count
    except Exception as e:
        print(f"Error occurred: {e}")
        return None




# Function to print scraped data
def print_data(article):
    print(f"Title: {article['title']}")
    
    # Print authors
    print(f"Authors: {', '.join(article['authors'])}")  # Access authors directly as a list

    print(f"Published in: {article['journal_name']}")
    print(f"Date of Publication: {article['Date']}")
    print(f"DOI: {article['doi']}")
    print(f"Abstract: {article['abstract']}")
    # print(f"Locations: {article['locations']}")
    print("-------------------------------")



# Function to scrape article data
def scrape_article_data():
    article = {}

    try:
        article['title'] = scrape_title(driver)
    except Exception as e:
        article['title'] = "Title not found"

    try:
        article['authors'] = scrape_authors(driver)  # Directly get the list of authors
    except Exception as e:
        article['authors'] = []  # Ensure authors is always a list

    
    
       # Extract authors and affiliations
    try:
        authors_with_affiliations = scrape_authors_with_affiliations(driver)
        article['authors_with_affiliations'] = authors_with_affiliations
    except Exception as e:
        article['authors_with_affiliations'] = []
    
    # Extract location data
    try:
        article['universities'] = [author['university'] for author in authors_with_affiliations]
        article['countries'] = [author['country'] for author in authors_with_affiliations]
        article['locations'] = [author['location'] for author in authors_with_affiliations]
    except Exception as e:
        article['universities'] = []
        article['countries'] = []
        article['locations'] = []


    
    try:
        article['Date'] = driver.find_element(By.XPATH, "//div[contains(@class, 'doc-abstract-pubdate')]").text.split(":")[1].strip()
        date_str = article["Date"]
        date_obj = datetime.strptime(date_str, "%d %B %Y")
        # Add month and year to JSON
        article["Month"] = date_obj.strftime("%B")
        article["Day"] = date_obj.day
        article["Year"] = date_obj.year
    except (ValueError, KeyError):
        print("Date format is incorrect or missing")

    try:
        article['abstract'] = driver.find_element(By.XPATH, "//div[@xplmathjax]").text
    except NoSuchElementException:
        article['abstract'] = "Abstract not found"

    
    # try:
    #     article['doi'] = driver.find_element(By.XPATH, "//a[contains(@href, 'doi.org')]").text
    # except NoSuchElementException:
    #     article['doi'] = "DOI not found"
    try:
    # Extract the full DOI URL from the href attribute
        article['doi'] = driver.find_element(By.XPATH, "//a[contains(@href, 'doi.org')]").get_attribute("href")
    except NoSuchElementException:
        article['doi'] = "DOI not found"


    # Extract total citations
    article['citations'] = get_total_citations(driver)

    article['type'] = "RESEARCH-ARTICLE"

    try:
        article['journal_name'] = driver.find_element(By.CLASS_NAME, "stats-document-abstract-publishedIn").text
        article['journal_name'] = article['journal_name'].replace("Published in:", "").replace("Early Access", "").strip()
        article['journal_name'] = article['journal_name'].replace("Published in:", "").replace("Early Access", "").strip()
        
        # If there are parentheses left, remove them
        article['journal_name'] = article['journal_name'].replace("(", "").replace(")", "").strip()
    except NoSuchElementException:
        article['journal_name'] = "Published in not found"


    # try:
    #     article['publisher'] = driver.find_element(By.XPATH, "//div[@class='u-pb-1 doc-abstract-publisher']//span[@class='title' and text()='Publisher: ']/following-sibling::span").text
    # except NoSuchElementException:
    #     article['publisher'] = "Publisher not found"
    
    # Extract keywords
    article['keywords'] = scrape_keywords(driver)

    # Extract ISSN information
    article['ISSN'] = extract_issn(driver)

    article['topic'] = "AI"

    article['website'] ="IEEE Xplore"

    
    return article



# Function to go to the next page using the "Next" button
def go_to_next_page():
    """Click on the 'Next' button to go to the next page."""
    try:
        # Wait for the 'Next' button to be clickable
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "next-btn"))
        )
        next_button.click()
        logging.info("Navigated to the next page.")
        return True  # Return True if next page is clicked
    except (NoSuchElementException, TimeoutException):
        logging.info("No more pages available or 'Next' button not found.")
        return False  # Return False if there is no next page button
    

# Function to initialize the JSON file if it does not exist
def initialize_json_file(filename):
    if not os.path.exists(filename):
        os.makedirs(os.path.dirname(filename), exist_ok=True)  # Create directories if they don't exist
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump([], json_file, indent=4, ensure_ascii=False)
        logging.info(f"Initialized new JSON file: {filename}")


def sanitize_text(data):
    """
    Recursively sanitize text fields in a dictionary or list by decoding Unicode escapes.
    """
    if isinstance(data, dict):
        return {key: sanitize_text(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_text(item) for item in data]
    elif isinstance(data, str):
        # Decode Unicode escape sequences in strings
        return data.encode('utf-8').decode('unicode_escape')
    elif isinstance(data, bytes):
        # If the data is in bytes, decode it to string
        return data.decode('utf-8')
    else:
        return data  # Return the data as is if it's not a dict, list, str, or bytes

# Function to append data incrementally to a JSON file
def save_to_json(data, filename):
    """
    Append a single sanitized data entry to the JSON file without overwriting existing content.
    """
    try:
        sanitized_data = sanitize_text(data)  # Preprocess data to sanitize text fields

        # Check if the file exists and is not empty
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            with open(filename, "r", encoding="utf-8") as json_file:
                try:
                    existing_data = json.load(json_file)  # Load existing JSON content
                    if not isinstance(existing_data, list):
                        existing_data = []  # Reset to list if the file contains invalid data
                except json.JSONDecodeError:
                    # If the file contains invalid JSON, start a new list
                    existing_data = []
        else:
            existing_data = []  # File doesn't exist or is empty

        # Add the sanitized data to the list
        existing_data.append(sanitized_data)

        # Write updated data back to the file
        with open(filename, "w", encoding="utf-8") as json_file:
            json.dump(existing_data, json_file, indent=4, ensure_ascii=False)

        logging.info(f"Data successfully appended to {filename}")
    except Exception as e:
        logging.error(f"Failed to append data to JSON: {e}")
    except IOError as e:
        logging.error(f"File operation failed: {e}")

# Main loop to scrape articles from multiple pages
page_number = 1
initialize_json_file("IEEE/DevOps.json")  

while True:
    logging.info(f"Scraping page {page_number}...")

    try:
        # Find all articles on the current page
        results = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "List-results-items"))
        )

        # Loop through the articles on the current page and scrape data
        for result in results:
            try:
                title_element = result.find_element(By.CSS_SELECTOR, "h3.text-md-md-lh a.fw-bold")
                link = title_element.get_attribute('href')
                title = title_element.text

                logging.info(f"Scraping article: {title}")

                # Open the article in a new tab and switch to that tab
                driver.execute_script("window.open(arguments[0], '_blank');", link)
                driver.switch_to.window(driver.window_handles[-1])

                # Scrape article data
                article = scrape_article_data()
                print_data(article)

                # Save each article incrementally to JSON
                save_to_json(article, filename="IEEE/DevOps.json")

                # Close the current article tab and switch back to the original tab
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            except (NoSuchElementException, TimeoutException) as e:
                logging.error(f"Error scraping article: {e}")
                if driver.window_handles:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

        # Check if there is a next page and go to the next page if available
        if not go_to_next_page():
            break  # Exit the loop if no more pages are available

        page_number += 1

    except TimeoutException:
        logging.error(f"Failed to load results for page {page_number}. Ending scraping.")
        break

# Close the driver
driver.quit()
