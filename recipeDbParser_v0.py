import os
import pandas as pd
import json
import re
import csv
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Function to check if the URL is valid
def is_valid_url(url):
    try:
        response = requests.get(url)
        return response.status_code == 200
    except:
        return False

# Function to extract and format the first two tables from the webpage
def extract_tables(url):
    df = pd.read_html(url)

    # Extract the first and second tables
    df1 = df[0]
    df2 = df[1]

    # Create json_file1 with the desired format
    json_file1_content = df1.set_index('Nutrient')['Quantity'].to_dict()

    # Create json_file2 with the desired format
    df2.reset_index(inplace=True)
    json_file2_content = df2.apply(lambda row: row.dropna().to_dict(), axis=1).to_dict()

    return json_file1_content, json_file2_content

# Function to click the "Show More" button and extract detailed nutritional information
def click_show_more_button(url):
    # Initialize the WebDriver (assuming Chrome)
    driver = webdriver.Chrome()

    try:
        # Open the provided URL
        driver.get(url)

        # Wait until the button is present and clickable
        wait = WebDriverWait(driver, 10)
        show_more_button = wait.until(EC.element_to_be_clickable((By.ID, 'myBtn')))

        # Click the button
        show_more_button.click()

        # Wait for the elements with the class 'bigRows' to be present
        big_rows_elements = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'bigRows')))

        # Collect the text of each element with the class 'bigRows'
        big_rows_texts = [element.text for element in big_rows_elements]

        # Grab the <h3> header text
        h3_header = driver.find_element(By.TAG_NAME, 'h3').text

        # Grab the elements with the class 'title'
        cuisine_origin_elements = driver.find_elements(By.CLASS_NAME, 'title')
        cuisine_origin = [element.text for element in cuisine_origin_elements]

        # Wait for the element with the ID 'steps' to be present
        try:
            steps_element = wait.until(EC.presence_of_element_located((By.ID, 'steps')))
            steps_paragraphs = steps_element.find_elements(By.TAG_NAME, 'p')
            instructions = [p.get_attribute('innerHTML') for p in steps_paragraphs]
        except:
            instructions = []

        # Return the collected data
        return {
            "title": h3_header,
            "Cuisine Origin": cuisine_origin,
            "details": big_rows_texts,
            "Instructions": instructions
        }

    finally:
        # Close the WebDriver
        driver.quit()

# Function to parse the detailed nutritional data
def parse_nutritional_data(data_list):
    nutritional_dict = {}
    for item in data_list:
        # Use regular expression to separate the key and value
        match = re.match(r'(.+)\s\((g|mg)\)\s(.+)', item)
        if match:
            key = match.group(1).strip()
            unit = match.group(2)
            value = match.group(3).strip()
            nutritional_dict[f"{key} ({unit})"] = value
    return nutritional_dict

# Main function to combine everything
def process_url(url):
    # Extract table data
    nutritional_profile, ingredients = extract_tables(url)

    # Click the "Show More" button and extract detailed nutritional data
    detailed_data = click_show_more_button(url)

    # Parse the detailed nutritional data
    detailed_nutritional_profile = parse_nutritional_data(detailed_data["details"])
    title = detailed_data["title"]
    cuisine_origin = detailed_data["Cuisine Origin"]
    instructions = detailed_data["Instructions"]

    # Combine everything into the final JSON structure
    final_json = {
        "title": title,
        "Cuisine Origin": cuisine_origin,
        "Estimated Nutritional Profile": nutritional_profile,
        "Ingredients": ingredients,
        "Estimated Nutritional Profile detailed": detailed_nutritional_profile,
        "Instructions": instructions
    }

    return final_json

# Function to log the URL existence status
def log_url_status(url, status, log_file):
    log_exists = os.path.exists(log_file)
    with open(log_file, 'a', newline='') as file:
        writer = csv.writer(file)
        if not log_exists:
            writer.writerow(["URL", "Exists"])
        writer.writerow([url, status])

# Function to handle multiple URLs
def handle_multiple_urls(start, end, output_file, log_file):
    all_data = []

    # Check if output file exists and load existing data
    if os.path.exists(output_file):
        with open(output_file, 'r') as file:
            try:
                all_data = json.load(file)
                if not isinstance(all_data, list):
                    all_data = []
            except json.JSONDecodeError:
                all_data = []
    else:
        all_data = []

    for i in range(start, end + 1):
        url = f'https://cosylab.iiitd.edu.in/recipedb/search_recipeInfo/{i}'
        if is_valid_url(url):
            log_url_status(url, True, log_file)
            data = process_url(url)
            all_data.append(data)
            print(f"Processed URL: {url}")
        else:
            log_url_status(url, False, log_file)
            print(f"Invalid URL: {url}")

    # Write the combined data to the output file
    with open(output_file, 'w') as file:
        json.dump(all_data, file, indent=2)

# Example usage
start_id = 2631
end_id = 2635  # Adjust this range for testing
output_file = 'output.json'
log_file = 'url_log.csv'
handle_multiple_urls(start_id, end_id, output_file, log_file)
