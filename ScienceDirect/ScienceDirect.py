import json
import logging
import re
import time
from selenium import webdriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up Chrome options
chrome_options = uc.ChromeOptions()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-webgl")
chrome_options.add_argument("--disable-application-cache")
chrome_options.add_argument("--disable-popup-blocking")

def init_driver():
    try:
        driver = uc.Chrome(options=chrome_options)
        logging.info("WebDriver initialized successfully")
        return driver
    except Exception as e:
        logging.error(f"Failed to initialize WebDriver: {e}")
        return None

def click_show_more_button(driver):
    try:
        show_more_btn = driver.find_element(By.ID, "show-more-btn")
        ActionChains(driver).move_to_element(show_more_btn).click().perform()
        time.sleep(2)
        logging.info("Clicked 'Show more' button.")
    except NoSuchElementException as e:
        logging.warning(f"Failed to click 'Show more' button: {e}")
    except Exception as e:
        logging.error(f"An error occurred while clicking the 'Show more' button: {e}")
        
def extract_titles(driver):
            try:
                title_element = driver.find_element(By.ID, "screen-reader-main-title")
                return title_element.text if title_element else ""
            except Exception as e:
                logging.warning(f"Failed to extract title: {e}")
                return ""

def extract_authors(driver):
    try:
        given_names = driver.find_elements(By.CLASS_NAME, "given-name")
        surnames = driver.find_elements(By.CLASS_NAME, "surname")
        authors = []
        if len(given_names) == len(surnames):
            for i in range(len(given_names)):
                full_name = f"{given_names[i].text} {surnames[i].text}"
                authors.append(full_name)
        else:
            logging.error("Mismatch in number of given names and surnames")
        return authors
    except Exception as e:
        logging.warning(f"Failed to extract authors: {e}")
        return []


def extract_author_info(driver):
    """
    Extracts author names and their affiliations in the required format from the webpage using the provided Selenium WebDriver.
    
    :param driver: The Selenium WebDriver object.
    :return: A list of dictionaries containing the author's name, university, country, and location.
    """
    # Extract all author button elements
    author_buttons = driver.find_elements(By.CSS_SELECTOR, ".author-group button")
    author_info = []
    authors_processed = set()  # To avoid duplicates

    # Loop through each author element to extract information
    for button in author_buttons:
        try:
            # Extract the full name of the author (First, Last)
            first_name = button.find_element(By.CSS_SELECTOR, ".given-name").text
            last_name = button.find_element(By.CSS_SELECTOR, ".surname").text
            full_name = f"{first_name} {last_name}"
        except Exception as e:
            full_name = "Name not found"
        
        # Extract the superscript numbers (e.g., [1], [2]) which correspond to affiliations
        author_superscripts = [sup.text for sup in button.find_elements(By.CSS_SELECTOR, ".author-ref sup")]
        
        # Find the affiliation elements for the author
        affiliations = driver.find_elements(By.CSS_SELECTOR, ".affiliation")
        
        # We store the author's affiliation details separately to avoid duplication
        author_affiliations = []

        # Loop through all affiliations and associate them with their corresponding superscripts
        for affiliation in affiliations:
            try:
                # Get the affiliation's text
                affiliation_text = affiliation.find_element(By.TAG_NAME, "dd").text.strip()
                sup_num = affiliation.find_element(By.TAG_NAME, "sup").text
                
                # Regex to capture university/institution and country
                match = re.search(r"(.+?),\s*([^,]+)$", affiliation_text)
                
                if match:
                    # Extract university and country from the regex match
                    university = match.group(1).strip()
                    country = match.group(2).strip()
                else:
                    # Log unparseable location and set 'Unknown' for missing country
                    logging.warning(f"Could not parse location: '{affiliation_text}'")
                    university = affiliation_text
                    country = "Unknown"
                
                # Check if the superscript matches the author's superscript
                if sup_num in author_superscripts:
                    # Build full location
                    full_location = f"{university}, {country}"

                    # Store the author's affiliation information if not already added
                    if (full_name, university, country) not in authors_processed:
                        author_affiliations.append({
                            "author": full_name,
                            "university": university,
                            "country": country,
                            "location": full_location
                        })
                        authors_processed.add((full_name, university, country))  # Mark as processed
            except Exception as e:
                print(f"Error processing affiliation for {full_name}: {e}")
        
        # After gathering all affiliations, append the author's complete info
        author_info.extend(author_affiliations)
    
    return sanitize_text(author_info)


def decode_text(text):
    try:
        # Attempt to decode if there are any escaped sequences
        return text.encode('latin1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Return text as is if decoding fails
        return text

def extract_abstracts(driver):
    try:
        abstract_element = driver.find_element(By.ID, "abstracts")
        return decode_text(abstract_element.text) if abstract_element else ""
    except Exception as e:
        logging.warning(f"Failed to extract abstracts: {e}")
        return ""

def extract_keywords(driver):
    try:
        keywords = driver.find_elements(By.CLASS_NAME, "keyword")
        return [keyword.text for keyword in keywords] if keywords else []
    except Exception as e:
        logging.warning(f"Failed to extract keywords: {e}")
        return []

def extract_doi(driver):
    try:
        doi_element = driver.find_element(By.CSS_SELECTOR, "a.anchor.doi.anchor-primary")
        doi_url = doi_element.get_attribute("href")
        if doi_url:
            return doi_url
        else:
            logging.warning(f"Could not extract DOI URL from the element: {doi_element}")
            return ""
    except NoSuchElementException:
        logging.warning("DOI element not found.")
        return ""
    except Exception as e:
        logging.warning(f"Failed to extract DOI: {e}")
        return ""


def extract_locations(driver):
    try:
        # Locate all affiliation elements
        location_elements = driver.find_elements(By.CSS_SELECTOR, "dl.affiliation dd")
        locations = []
        universities = []
        countries = []

        for element in location_elements:
            location_text = element.text.strip()

            # Regex to capture university/institution and country
            match = re.search(r"(.+?),\s*([^,]+)$", location_text)
            if match:
                university = match.group(1).strip()
                country = match.group(2).strip()
                # Build full location
                full_location = f"{university}, {country}"
                
                # Append values
                locations.append(full_location)
                if university not in universities:
                    universities.append(university)
                if country not in countries:
                    countries.append(country)
            else:
                # Log unparseable location and set 'Unknown' for missing country
                logging.warning(f"Could not parse location: '{location_text}'")
                locations.append(location_text)
                if location_text not in universities:
                    universities.append(location_text)
                if "Unknown" not in countries:
                    countries.append("Unknown")

        return sanitize_text({
            "universities": universities,
            "countries": countries,
            "locations": locations
        })

    except Exception as e:
        logging.warning(f"Failed to extract locations: {e}")
        return {
            "universities": [],
            "countries": [],
            "locations": []
        }
    
def extract_publication_dates(driver):
    try:
        # Locate the paragraph containing the dates
        dates_paragraph = driver.find_element(By.CSS_SELECTOR, "p.u-margin-s-bottom").text

        # Regex to match all dates in the format "30 April 2024"
        date_matches = re.findall(r"(\d{1,2}) (\w+) (\d{4})", dates_paragraph)

        # Extract only the "Available online" date, which is the fourth date in the list
        if date_matches and len(date_matches) > 3:
            day, month, year = date_matches[3]  # The "Available online" date is the fourth date
            available_online_date = [int(day), month, int(year)]
            return available_online_date
        else:
            logging.warning("No 'Available online' date found in the expected format.")
            return None
    except Exception as e:
        logging.error(f"Failed to extract 'Available online' date: {e}")
        return None
    
def extract_journal_name(driver):
    try:
        # Wait for the element with ID "publication-title" to become visible
        journal_name_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "publication-title"))
        )
        journal_name = journal_name_element.text
        return journal_name
    except Exception as e:
        logging.warning(f"Failed to extract journal name: {e}")
        return ""


def extract_citation_count_from_page(driver):
    try:
        # Locate the citation count header directly
        cited_by_header = driver.find_element(By.XPATH, "//header[@id='citing-articles-header']/h2")
        
        # Extract the text content
        cited_by_text = cited_by_header.text.strip()  # Example: "Cited by (7)"
        
        # Parse the number of citations
        citation_count = int(cited_by_text.split('(')[-1].strip(')'))
        return citation_count

    except Exception as e:
        logging.warning(f"Failed to extract citation count: {e}")
        return 0



def scrape_article_data(driver):
    article = {}

    try:
        article['title'] = extract_titles(driver)
    except Exception as e:
        article['title'] = "Ttile not found"  
        logging.error(f"Error extracting titles: {e}")

    try:
        # Authors
        article['authors'] = extract_authors(driver) 
    except Exception as e:
        article['authors'] = []  
        logging.error(f"Error extracting authors: {e}")

    try:
        # Authors with affiliations
        article['authors_with_affiliations'] = extract_author_info(driver)
    except Exception as e:
        article['authors_with_affiliations'] = []  
        logging.error(f"Error extracting authors with affiliations: {e}")


    try:
    # Extract the "Available online" publication date components
        available_online_date = extract_publication_dates(driver)

        if available_online_date:
            day, month, year = available_online_date
            # Update the article dictionary
            article['Date'] = f"{day} {month} {year}"
            article['Day'] = day
            article['Month'] = month
            article['Year'] = year
        else:
            # If extraction fails, set default values
            article['Date'] = "Date not found"
            article['Day'] = "Day not found"
            article['Month'] = "Month not found"
            article['Year'] = "Year not found"
    except Exception as e:
        # Handle exceptions during parsing
        article['Date'] = "Date not found"
        article['Day'] = "Day not found"
        article['Month'] = "Month not found"
        article['Year'] = "Year not found"
        logging.error(f"Error parsing publication date: {e}")


    try:
        # Abstracts
        article['abstract'] = extract_abstracts(driver)
    except Exception as e:
        article['abstract'] = "Abstract not found"  
        logging.error(f"Error extracting abstracts: {e}")

    try:
        # DOI(s)
        article['doi'] = extract_doi(driver)
    except Exception as e:
        article['doi'] = "DOI not found" 
        logging.error(f"Error extracting DOIs: {e}")

    try:
        # Extract citation count from the page
        article['citations'] = extract_citation_count_from_page(driver)
    except Exception as e:
        article['citations'] = 0
        logging.error(f"Error extracting citation count: {e}")

    article['type'] = "RESEARCH-ARTICLE"
    
    try:
        # Extract journal name
        article['journal_name'] = extract_journal_name(driver)
    except Exception as e:
        article['journal_name'] = "Journal name not found"
        logging.error(f"Error extracting journal name: {e}")

    try:
    # Extract locations, universities, and countries
        location_data = extract_locations(driver)
        
        # Set article fields with extracted data
        article['universities'] = location_data.get('universities', ["N/A"])
        article['countries'] = location_data.get('countries', ["N/A"])
    except Exception as e:
    # Handle error and assign default values
        article['universities'] = ["N/A"]
        article['countries'] = ["N/A"]
        logging.error(f"Error extracting location details: {e}")

    try:
        # Keywords
        article['keywords'] = extract_keywords(driver)
    except Exception as e:
        article['keywords'] = [] 
        logging.error(f"Error extracting keywords: {e}")

    article['topic'] = "DevOps"

    article['website'] ="Science Direct"

    # Ensure that we capture even incomplete data and print/save it
    return article

def print_article_data(article_data):
    try:
        # Print formatted article data (even if incomplete)
        logging.info("Article Data:")
        
        # Ensure title exists in article_data
        logging.info(f"Title: {', '.join(article_data.get('title', ['N/A']))}")
        
        # Ensure abstract exists in article_data
        logging.info(f"Abstract: {', '.join(article_data.get('abstract', ['N/A']))}")
        
        # Ensure keywords exists in article_data
        logging.info(f"Keywords: {', '.join(article_data.get('keywords', ['N/A']))}")
        
        # Ensure DOI exists in article_data
        logging.info(f"DOI: {', '.join(article_data.get('doi', ['N/A']))}")
        
        # Ensure authors exists in article_data
        logging.info(f"Authors: {', '.join(article_data.get('authors', ['N/A']))}")

        
    except Exception as e:
        logging.error(f"Failed to print article data: {e}")



def initialize_json_file(filename="ScienceDirect/DevOps1.json"):
    """
    Initialize the JSON file by creating it with an empty list if it doesn't exist.
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Check if the file already exists
        if not os.path.isfile(filename):
            with open(filename, "w") as json_file:
                json.dump([], json_file, indent=4)  # Create an empty JSON array
            logging.info(f"Initialized new JSON file: {filename}")
    except Exception as e:
        logging.error(f"Failed to initialize JSON file: {e}")


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
        return data

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



def main_scraper(keyword):
    current_page = 1
    turn_it = True

    # Construct the URL and load the search page with the keyword
    web_site = f"https://www.sciencedirect.com/search?qs={keyword}&show=100&offset=0&articleTypes=FLA&accessTypes=openaccess"
    driver.get(web_site)
    time.sleep(4)

    # Select the "Research articles" checkbox
    try:
        # Find the "Research articles" checkbox by its id (articleTypes-FLA)
        research_article_checkbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "articleTypes-FLA"))
        )
        # Use JavaScript to click the checkbox if it's not already selected
        if not research_article_checkbox.is_selected():
            driver.execute_script("arguments[0].click();", research_article_checkbox)
            logging.info("Selected 'Research articles' filter.")
        else:
            logging.info("'Research articles' filter is already selected.")
    except TimeoutException:
        logging.error("Failed to locate the 'Research articles' checkbox.")

    try:
        # Find the "Open access" checkbox by its id (accessTypes-openaccess)
        open_access_checkbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "accessTypes-openaccess"))
        )
        # Use JavaScript to click the checkbox if it's not already selected
        if not open_access_checkbox.is_selected():
            driver.execute_script("arguments[0].click();", open_access_checkbox)
            logging.info("Selected 'Open access' filter.")
        else:
            logging.info("'Open access' filter is already selected.")
    except TimeoutException:
        logging.error("Failed to locate the 'Open access' checkbox.")

    while turn_it:
        logging.info(f"Scraping page {current_page}...")

        # Load the next page of results using pagination
        web_site = f"https://www.sciencedirect.com/search?qs={keyword}&show=100&offset={(current_page - 1) * 100}&articleTypes=FLA&accessTypes=openaccess"
        driver.get(web_site)
        time.sleep(4)

        try:
            results_div = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "srp-results-list"))
            )
            journals = results_div.find_elements(By.CLASS_NAME, "result-item-container")
        except TimeoutException:
            logging.error("Results section not found or page load timed out.")
            break

        if not journals:
            logging.info("No more journals found, ending pagination.")
            turn_it = False
            break

        visited_links = set()  # To track visited URLs

        for index, journal in enumerate(journals):
            try:
                # Extract the article link and title
                url_element = journal.find_element(By.CLASS_NAME, "result-list-title-link")
                url = url_element.get_attribute("href")

                if url in visited_links:
                    continue

                visited_links.add(url)

                # Open the journal URL in a new tab
                driver.execute_script("window.open(arguments[0], '_blank');", url)
                driver.switch_to.window(driver.window_handles[-1])

                # Click "Show more" button
                click_show_more_button(driver)

                # Scrape article data
                article_data = scrape_article_data(driver)

                # Save immediately to JSON after processing each article
                save_to_json(article_data, filename="ScienceDirect/DevOps1.json")

                # Print article data
                print_article_data(article_data)

                logging.info(f"Collected journal data for: {article_data['title']}")

                # Close the new tab and switch back to the original tab
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            except (NoSuchElementException, IndexError) as e:
                logging.error(f"Error collecting journal data: {e}")

        current_page += 1

    logging.info("Scraping completed.")


if __name__ == "__main__":
    try:
        driver = init_driver()
        if driver is None:
            raise Exception("Failed to initialize WebDriver.")
        main_scraper("DevOps")
    finally:
        if driver:
            driver.quit()
            logging.info("WebDriver closed successfully")
