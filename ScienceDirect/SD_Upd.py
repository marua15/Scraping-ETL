import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Function to scrape journal data from SCImago
def scrape_journal_data(journal_name, driver):
    try:
        # Step 1: Access SCImago website
        driver.get("https://www.scimagojr.com/")
        wait = WebDriverWait(driver, 10)

        # Step 2: Search for the journal by name
        search_box = wait.until(EC.visibility_of_element_located((By.ID, "searchinput")))
        search_box.clear()
        search_box.send_keys(journal_name)
        search_box.send_keys(Keys.RETURN)

        # Step 3: Select the journal link
        journal_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'journalsearch.php') and contains(@href, 'sid')]")))
        journal_link.click()

        # Step 4: Close any pop-up ad if present
        try:
            close_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, "ns-jhssl-e-5.close-button")))
            close_button.click()
        except Exception:
            pass  # No ad to close, continue

        # Step 5: Retrieve ISSN
        try:
            issn_div = driver.find_element(By.XPATH, "//h2[text()='ISSN']/following-sibling::p")
            issn_text = issn_div.text.strip()
        except Exception as e:
            print(f"Error retrieving ISSN for '{journal_name}': {e}")
            issn_text = "N/A"

        # Step 6: Click the table button to view quartile data
        table_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".combo_buttons .combo_button.table_button")))
        table_button.click()
        time.sleep(2)  # Allow table to load

        # Step 7: Scrape table data containing Quartiles
        table = driver.find_element(By.XPATH, "//div[@class='cellslide']/table")
        rows = table.find_elements(By.XPATH, ".//tbody/tr")
        data = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) == 3:
                category, year, quartile = [col.text.strip() for col in cols]
                year = int(year)  # Convert the year to integer
                data.append({"Year": year, "Quartile": quartile})

        return {"ISSN": issn_text, "QuartileData": data}

    except Exception as e:
        print(f"Error occurred while scraping data for {journal_name}: {e}")
        return {"ISSN": "N/A", "QuartileData": []}

# Function to append Quartile data to the publisher field incrementally
def append_quartile_to_publisher_incrementally(article, driver):
    journal_name = article.get('journal_name', '').strip()

    # Ensure the year is an integer
    year = article.get('Year', 0)
    if isinstance(year, str) and year.isdigit():
        year = int(year)
    elif not isinstance(year, int):
        year = 0  # Default to 0 if the year is neither a valid string nor an integer

    # Initialize publisher field
    article['publisher'] = {"name": journal_name, "ISSN": "N/A", "Quartile": ""}

    # Skip if no journal name is provided
    if not journal_name:
        return article

    # Get the quartile data and ISSN for the journal from SCImago
    scraped_data = scrape_journal_data(journal_name, driver)
    quartile_data = scraped_data["QuartileData"]
    issn_text = scraped_data["ISSN"]

    # Update ISSN in the publisher field
    article['publisher']['ISSN'] = issn_text

    # Try to find the quartile for the article's year, and if not found, fallback to previous years
    if quartile_data and year:
        for i in range(0, 10):  # Check current year and up to 9 previous years
            target_year = year - i
            for entry in quartile_data:
                if entry['Year'] == target_year:
                    article['publisher']['Quartile'] = entry['Quartile']
                    break
            if article['publisher']['Quartile']:  # Exit once quartile is found
                break

    # Remove the journal_name field before returning the updated article
    article.pop('journal_name', None)

    return article



# Main execution block
def main():
    # Specify the path to ChromeDriver
    chrome_driver_path = "chromedriver-win64/chromedriver.exe"  # Replace with your ChromeDriver path

    # Initialize the Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in headless mode if UI is not required
    from selenium.webdriver.chrome.service import Service
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    # Load original data from JSON file
    try:
        with open('ScienceDirect/DevOps.json', 'r', encoding='utf-8') as f:
            original_data = json.load(f)
    except UnicodeDecodeError as e:
        print(f"Error decoding the JSON file: {e}")
        return

    # Open the updated JSON file in append mode
    output_file = 'ScienceDirect/DevOps_upd1.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('[\n')  # Start the JSON array

    for idx, article in enumerate(original_data):
        updated_article = append_quartile_to_publisher_incrementally(article, driver)

        # Append each updated article to the JSON file
        with open(output_file, 'a', encoding='utf-8') as f:
            json.dump(updated_article, f, indent=4, ensure_ascii=False)
            if idx < len(original_data) - 1:
                f.write(',\n')  # Add a comma after each article except the last
            else:
                f.write('\n')  # No comma for the last article

    # Close the JSON array
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(']\n')

    # Close the driver after scraping
    driver.quit()

# Run the script
if __name__ == "__main__":
    main()
