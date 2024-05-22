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
from concurrent.futures import ThreadPoolExecutor, as_completed

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

        # Locate the <ul> element with the class 'collection'
        collection_ul = driver.find_element(By.CLASS_NAME, 'collection')

        # Extract the necessary information from the <li> elements
        li_elements = collection_ul.find_elements(By.TAG_NAME, 'li')

        cuisine_origin = li_elements[0].text.strip() if len(li_elements) > 0 else ""
        dietary_details = driver.find_element(By.ID, 'dietary-text').text.strip() if len(li_elements) > 1 else ""
        preparation_time = li_elements[2].text.strip() if len(li_elements) > 2 else ""
        source_info = li_elements[3].find_element(By.TAG_NAME, 'a').get_attribute('href') if len(li_elements) > 3 else ""

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
            "Dietary Details": dietary_details,
            "Preparation Time": preparation_time,
            "Source Info": source_info,
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

# Function to parse the Cuisine Origin into nested structure
def parse_cuisine_origin(cuisine_origin):
    cuisine_origin = cuisine_origin.replace("Cuisine\n", "").strip()  # Clean up the input
    parts = cuisine_origin.split(" >> ")
    cuisine_dict = {
        "continent": parts[0] if len(parts) > 0 else "",
        "region": parts[1] if len(parts) > 1 else "",
        "country": parts[2] if len(parts) > 2 else ""
    }
    if cuisine_dict["country"] == "Indian":
        cuisine_dict["state"] = ""
    return cuisine_dict

# Function to parse the preparation time into a nested structure
def parse_preparation_time(preparation_time):
    preparation_time = preparation_time.replace("Preparation Time\n", "").strip()
    cooking_time_match = re.search(r'Cooking Time - (\d+) minutes', preparation_time)
    prep_time_match = re.search(r'Preparation Time - (\d+) minutes', preparation_time)
    
    cooking_time = int(cooking_time_match.group(1)) if cooking_time_match else 0
    prep_time = int(prep_time_match.group(1)) if prep_time_match else 0
    total_time = cooking_time + prep_time
    
    return {
        "Cooking Time (Minutes)": cooking_time,
        "Preparation Time (Minutes)": prep_time,
        "Total Time (Minutes)": total_time
    }

# Main function to combine everything
def process_url(url):
    # Extract table data
    nutritional_profile, ingredients = extract_tables(url)

    # Click the "Show More" button and extract detailed nutritional data
    detailed_data = click_show_more_button(url)

    # Parse the detailed nutritional data
    detailed_nutritional_profile = parse_nutritional_data(detailed_data["details"])
    title = detailed_data["title"]
    cuisine_origin = parse_cuisine_origin(detailed_data["Cuisine Origin"])
    time_data = parse_preparation_time(detailed_data["Preparation Time"])
    dietary_details = detailed_data["Dietary Details"]
    source_info = detailed_data["Source Info"]
    instructions = detailed_data["Instructions"]

    # Combine everything into the final JSON structure
    final_json = {
        "title": title,
        "Cuisine Origin": cuisine_origin,
        "Dietary Details": dietary_details,
        "Time": time_data,
        "Source Info": source_info,
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

# Function to process a single URL (helper function for parallel execution)
def process_single_url(i, log_file):
    url = f'https://cosylab.iiitd.edu.in/recipedb/search_recipeInfo/{i}'
    if is_valid_url(url):
        log_url_status(url, True, log_file)
        data = process_url(url)
        print(f"Processed URL: {url}")
        return data
    else:
        log_url_status(url, False, log_file)
        print(f"Invalid URL: {url}")
        return None

# Function to handle multiple URLs in parallel
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

    # Create a thread pool to process URLs in parallel
    with ThreadPoolExecutor(max_workers=40) as executor:
        futures = [executor.submit(process_single_url, i, log_file) for i in range(start, end + 1)]

        for future in as_completed(futures):
            result = future.result()
            if result:
                all_data.append(result)

    # Write the combined data to the output file
    with open(output_file, 'w') as file:
        json.dump(all_data, file, indent=2)

# Example usage
start_id = 2631
end_id = 2670  # Adjust this range for testing
output_file = 'output.json'
log_file = 'url_log.csv'
handle_multiple_urls(start_id, end_id, output_file, log_file)
