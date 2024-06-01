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

# Function to modify the nutritional profile
def transform_nutritional_profile(nutritional_profile):
    transformed_profile = {}
    for key, value in nutritional_profile.items():
        if key == "Calories":
            transformed_profile[key] = int(value.replace('g', '').strip())
        else:
            new_key = key.replace("Fat", "Fat(g)").replace("Carbs", "Carbs(g)").replace("Protein", "Protein(g)")
            transformed_profile[new_key] = int(value.replace('g', '').strip())
    return transformed_profile

def convert_nutritional_profile(nutritional_profile):
    # Initialize an empty dictionary for the converted profile
    converted_profile = {}
    
    # Loop through each key-value pair in the nutritional profile
    for key, value in nutritional_profile.items():
        # Split the value to remove the "key\n" part and get the actual value
        key_base, actual_value = value.split('\n')
        
        # Separate the numeric part from the unit
        numeric_value = ''.join([char for char in actual_value if char.isdigit() or char == '.'])
        unit = ''.join([char for char in actual_value if not char.isdigit() and char != '.'])
        
        # Create the new key by appending the unit in parentheses to the original key
        new_key = "{}({})".format(key_base, unit)
        
        # Convert the numeric value to a float
        numeric_value = float(numeric_value)
        
        # Add the new key-value pair to the converted profile
        converted_profile[new_key] = numeric_value
    
    # Return the updated dictionary
    return converted_profile

# Function to extract servings and nutritional information from the source URL
def extract_servings_from_source(source_url, source_log_file):
    # Validate the URL before proceeding
    if not is_valid_url(source_url):
        log_url_status(source_url, False, source_log_file)
        print(f"Invalid URL: {source_url}")
        return {
            "Time (from Source)": {
                "Prep Time (Minutes)": 0,
                "Cook Time (Minutes)": 0,
                "Additional Time (Minutes)": 0,
                "Total Time (Minutes)": 0
            },
            "Servings": 0,
            "Yield": "",
            "About Recipe": "",
            "Nutritional Profile (from Source)": {},
            "Nutritional Profile Detailed (from Source)": {},
            "Ingredients (from source)": []
        }

    # Initialize the WebDriver (assuming Chrome)
    driver = webdriver.Chrome()

    try:
        # Open the source URL
        driver.get(source_url)

        # Wait until the div with id 'mntl-recipe-details_1-0' is present
        wait = WebDriverWait(driver, 10)
        details_div = wait.until(EC.presence_of_element_located((By.ID, 'mntl-recipe-details_1-0')))

        # Navigate to the required element
        content_div = details_div.find_element(By.CLASS_NAME, 'mntl-recipe-details__content')
        items = content_div.find_elements(By.CLASS_NAME, 'mntl-recipe-details__item')

        data = {
            "Time (from Source)": {
                "Prep Time (Minutes)": 0,
                "Cook Time (Minutes)": 0,
                "Additional Time (Minutes)": 0,
                "Total Time (Minutes)": 0
            },
            "Servings": 0,
            "Yield": "",
            "About Recipe": ""
        }

        def convert_to_minutes(time_str):
            """Convert a time string into minutes."""
            minutes = 0
            time_parts = re.findall(r'(\d+)\s*(hr|min|hour|minute|hrs|hours|minutes)', time_str.lower())
            for amount, unit in time_parts:
                if 'hr' in unit or 'hour' in unit:
                    minutes += int(amount) * 60
                elif 'min' in unit or 'minute' in unit:
                    minutes += int(amount)
            return minutes
        
        def convert_to_numeric(servings_str):
            """Convert servings string to a numeric value."""
            match = re.search(r'\d+', servings_str)
            if match:
                return int(match.group())
            return 0

        for item_div in items:
            try:
                label_div = item_div.find_element(By.CLASS_NAME, 'mntl-recipe-details__label')
                value_div = item_div.find_element(By.CLASS_NAME, 'mntl-recipe-details__value')
                
                # Use get_attribute('textContent') to capture the text
                label_text = label_div.get_attribute('textContent').strip()
                value_text = value_div.get_attribute('textContent').strip()

                if label_text == "Prep Time:":
                    data["Time (from Source)"]["Prep Time (Minutes)"] = convert_to_minutes(value_text)
                elif label_text == "Cook Time:":
                    data["Time (from Source)"]["Cook Time (Minutes)"] = convert_to_minutes(value_text)
                elif label_text == "Additional Time:":
                    data["Time (from Source)"]["Additional Time (Minutes)"] = convert_to_minutes(value_text)
                elif label_text == "Total Time:":
                    data["Time (from Source)"]["Total Time (Minutes)"] = convert_to_minutes(value_text)
                elif label_text == "Servings:":
                    data["Servings"] = convert_to_numeric(value_text)
                elif label_text == "Yield:":
                    data["Yield"] = value_text

            except Exception as e:
                print(f"Error processing item_div: {e}")

        # Extract nutritional information
        try:
            nutrition_div = driver.find_element(By.ID, 'mntl-nutrition-facts-summary_1-0')
            table_body = nutrition_div.find_element(By.CLASS_NAME, 'mntl-nutrition-facts-summary__table-body')
            rows = table_body.find_elements(By.CLASS_NAME, 'mntl-nutrition-facts-summary__table-row')

            nutritional_profile = {}
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if len(cells) == 2:
                    key = cells[0].get_attribute('textContent').strip()
                    value = cells[1].get_attribute('textContent').strip()
                    if key and value:
                        nutritional_profile[value] = key  # Swap key and value

            # Transform the nutritional profile
            data["Nutritional Profile (from Source)"] = transform_nutritional_profile(nutritional_profile)

            # Extract detailed nutritional information
            detailed_nutrition_div = driver.find_element(By.ID, 'mntl-nutrition-facts-label_1-0')
            wrapper_div = detailed_nutrition_div.find_element(By.CLASS_NAME, 'mntl-nutrition-facts-label__wrapper')
            contents_div = wrapper_div.find_element(By.CLASS_NAME, 'mntl-nutrition-facts-label__contents')
            table = contents_div.find_element(By.CLASS_NAME, 'mntl-nutrition-facts-label__table')
            tbody = table.find_element(By.CLASS_NAME, 'mntl-nutrition-facts-label__table-body')
            rows = tbody.find_elements(By.TAG_NAME, 'tr')

            detailed_nutritional_profile = {}

            for row in rows:
                td_elements = row.find_elements(By.TAG_NAME, 'td')
                # Extract the text from the <span> element
                if len(td_elements) == 2:
                    span_element = td_elements[0].find_element(By.CLASS_NAME, 'mntl-nutrition-facts-label__nutrient-name')
                    key = span_element.get_attribute('textContent').strip()
                    detailed_nutritional_profile[key] = td_elements[0].get_attribute('textContent').strip()

            data["Nutritional Profile Detailed (from Source)"] = convert_nutritional_profile(detailed_nutritional_profile)

        except Exception as e:
            print(f"Error extracting nutritional information: {e}")
            data["Nutritional Profile (from Source)"] = {}
            data["Nutritional Profile Detailed (from Source)"] = {}

        # Extract ingredient information
        try:
            ingredients_div = driver.find_element(By.CLASS_NAME, 'mntl-structured-ingredients__list')
            ingredient_items = ingredients_div.find_elements(By.CLASS_NAME, 'mntl-structured-ingredients__list-item')

            unicode_fractions = {
                "\u00bd": "1/2",
                "\u00bc": "1/4",
                "\u00be": "3/4",
                "\u2153": "1/3",
                "\u2154": "2/3",
                "\u215b": "1/8",
                "\u215c": "3/8",
                "\u215d": "5/8",
                "\u215e": "7/8"
            }

            ingredients = []
            for item in ingredient_items:
                spans = item.find_elements(By.TAG_NAME, 'span')
                quantity = spans[0].get_attribute('textContent').strip() if len(spans) > 0 else ""
                unit = spans[1].get_attribute('textContent').strip() if len(spans) > 1 else ""
                name = spans[2].get_attribute('textContent').strip() if len(spans) > 2 else ""

                # Replace Unicode fractions with their textual representation
                for unicode_char, fraction in unicode_fractions.items():
                    quantity = quantity.replace(unicode_char, fraction)

                ingredient = f"{quantity} {unit} {name}".strip()
                ingredients.append(ingredient)

            data["Ingredients (from source)"] = ingredients

        except Exception as e:
            print(f"Error extracting ingredients information: {e}")
            data["Ingredients (from source)"] = []

        # Extract the text inside <p> element with class "article-subheading type--dog"
        try:
            about_recipe_element = driver.find_element(By.CLASS_NAME, 'article-subheading.type--dog')
            data["About Recipe"] = about_recipe_element.text.strip()
        except Exception as e:
            print(f"Error extracting about recipe information: {e}")
            data["About Recipe"] = ""

        log_url_status(source_url, True, source_log_file)
        return data

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
def process_url(url, source_log_file):
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

    # Extract servings and nutritional information from the source URL
    servings_data = extract_servings_from_source(source_info, source_log_file)

    # Combine everything into the final JSON structure
    final_json = {
        "title": title,
        "Cuisine Origin": cuisine_origin,
        "Dietary Details": dietary_details,
        "Time": time_data,
        "Source Info": source_info,
        "Servings": servings_data["Servings"],
        "Yield": servings_data["Yield"],
        "Time (from Source)": servings_data["Time (from Source)"],
        "Nutritional Profile (from Source)": servings_data["Nutritional Profile (from Source)"],
        "Nutritional Profile Detailed (from Source)": servings_data["Nutritional Profile Detailed (from Source)"],
        "Estimated Nutritional Profile": nutritional_profile,
        "Ingredients": ingredients,
        "Ingredients (from source)": servings_data["Ingredients (from source)"],
        "Estimated Nutritional Profile detailed": detailed_nutritional_profile,
        "Instructions": instructions,
        "About Recipe": servings_data["About Recipe"]
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
def process_single_url(i, log_file, source_log_file):
    url = f'https://cosylab.iiitd.edu.in/recipedb/search_recipeInfo/{i}'
    if is_valid_url(url):
        log_url_status(url, True, log_file)
        data = process_url(url, source_log_file)
        print(f"Processed URL: {url}")
        return data
    else:
        log_url_status(url, False, log_file)
        print(f"Invalid URL: {url}")
        return None

# Function to handle multiple URLs in parallel
def handle_multiple_urls(start, end, output_file, log_file, source_log_file):
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
        futures = [executor.submit(process_single_url, i, log_file, source_log_file) for i in range(start, end + 1)]

        for future in as_completed(futures):
            result = future.result()
            if result:
                all_data.append(result)

    # Write the combined data to the output file
    with open(output_file, 'w') as file:
        json.dump(all_data, file, indent=2)

# Example usage
start_id = 4003
end_id = 4023  # Adjust this range for testing
output_file = 'output.json'
log_file = 'url_log.csv'
source_log_file = 'source_log.csv'
handle_multiple_urls(start_id, end_id, output_file, log_file, source_log_file)
