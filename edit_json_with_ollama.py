import json
import ollama
import time

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", 
    "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
    "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", 
    "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", "Lakshadweep", "Delhi", "Puducherry", "Ladakh", "Jammu and Kashmir"
]

def read_json(file_path):
    """Read a JSON file and return the data."""
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def write_json(file_path, data):
    """Write data to a JSON file."""
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def get_recipe_state(recipe_title):
    """Get the state(s) associated with a recipe title using Ollama."""
    prompt = f"Identify the Indian state(s) associated with the recipe titled '{recipe_title}'. If it belongs to multiple states, list them all."
    response = ollama.generate(model='llama3', prompt=prompt)
    generated_value = response['response']
    print(f"Printing for debugging: generated_value for state extraction {generated_value}")
    # Extract state names from the response
    states = extract_state_names(generated_value)
    return states

def extract_state_names(response):
    """Extract state names from the response."""
    response_lower = response.lower()
    found_states = []
    for state in INDIAN_STATES:
        state_lower = state.lower()
        if state_lower in response_lower:
            found_states.append(state)
    return found_states

# def get_nutritional_info(ingredient_name, quantity, unit):
#     """Get nutritional information for an ingredient using Ollama."""
#     prompt = f"Provide the nutritional information specifically for {quantity} {unit} of {ingredient_name} including Energy (kcal), Carbohydrates (g), Protein (g), and Total Lipid (Fat) (g)."
#     response = ollama.generate(model='llama3', prompt=prompt)
#     generated_value = response['response']
#     print(f"Printing for debugging: generated_value {generated_value}")
#     # Parse the response to extract nutritional information
#     nutritional_info = parse_nutritional_info(generated_value)
#     return nutritional_info

# def parse_nutritional_info(response):
#     """Parse the response to extract nutritional information."""
#     nutritional_info = {
#         "Energy (kcal)": "",
#         "Carbohydrates": "",
#         "Protein (g)": "",
#         "Total Lipid (Fat) (g)": ""
#     }
#     for line in response.split('\n'):
#         line_lower = line.lower()
#         if 'energy' in line_lower or 'calories' in line_lower:
#             nutritional_info["Energy (kcal)"] = extract_string_value(line)
#         elif 'carbohydrates' in line_lower:
#             nutritional_info["Carbohydrates"] = extract_string_value(line)
#         elif 'protein' in line_lower:
#             nutritional_info["Protein (g)"] = extract_string_value(line)
#         elif 'total lipid' in line_lower or 'fat' in line_lower:
#             nutritional_info["Total Lipid (Fat) (g)"] = extract_string_value(line)
#     print(f"Printing for debugging: parsed nutritional_info {nutritional_info}")
#     return nutritional_info

# def extract_string_value(line):
#     """Extract the value from a line of text."""
#     parts = line.split(':', 1)
#     if len(parts) > 1:
#         return parts[1].strip()
#     return ""

def update_ingredients(ingredients):
    """Update the nutritional values for each ingredient."""
    for key, value in ingredients.items():
        ingredient_name = value.get('Ingredient Name', '')
        quantity = value.get('Quantity', '')
        unit = value.get('Unit', '')
        if ingredient_name and quantity and unit:
            print(f"Processing ingredient: {ingredient_name}, Quantity: {quantity}, Unit: {unit}")
            start_time = time.time()
            # nutritional_info = get_nutritional_info(ingredient_name, quantity, unit)
            # print(f"Printing for debugging: Nutritional info {nutritional_info}")
            end_time = time.time()
            print(f"Processed in {end_time - start_time} seconds")
            # value['Energy (kcal)'] = nutritional_info.get('Energy (kcal)', "")
            # value['Carbohydrates'] = nutritional_info.get('Carbohydrates', "")
            # value['Protein (g)'] = nutritional_info.get('Protein (g)', "")
            # value['Total Lipid (Fat) (g)'] = nutritional_info.get('Total Lipid (Fat) (g)', "")

def edit_json(data):
    """Edit the JSON data by updating the 'state' key for each recipe and adding/updating 'Ingredients (from LLM)' key."""
    if isinstance(data, list):
        for recipe in data:
            title = recipe.get('title', '')
            cuisine_origin = recipe.get('Cuisine Origin', {})
            if title and 'state' in cuisine_origin:
                states = get_recipe_state(title)
                cuisine_origin['state'] = states
            # Copy the content of the "Ingredients" key to "Ingredients (from LLM)"
            # if 'Ingredients' in recipe:
            #     recipe['Ingredients (from LLM)'] = recipe['Ingredients']
            #     update_ingredients(recipe['Ingredients (from LLM)'])
    else:
        print("Data format is not as expected. Expected a list of recipes.")
    return data

def main():
    input_file = '/Users/kabyabasu/Desktop/learning/selenium_task/output_copy.json'
    output_file = '/Users/kabyabasu/Desktop/learning/selenium_task/output_new38.json'

    # Read the JSON file
    data = read_json(input_file)

    # Edit the JSON data
    print("Starting JSON data editing...")
    data = edit_json(data)
    print("Finished JSON data editing.")

    # Write the modified data back to the JSON file
    write_json(output_file, data)
    print("Data written to output file.")

if __name__ == '__main__':
    main()
