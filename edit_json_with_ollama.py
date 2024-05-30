import json
import ollama

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
    print(response)
    generated_value = response['response']
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

def edit_json(data):
    """Edit the JSON data by updating the 'state' key for each recipe."""
    if isinstance(data, list):
        for recipe in data:
            title = recipe.get('title', '')
            cuisine_origin = recipe.get('Cuisine Origin', {})
            if title and 'state' in cuisine_origin:
                states = get_recipe_state(title)
                cuisine_origin['state'] = states
    else:
        print("Data format is not as expected. Expected a list of recipes.")
    return data

def main():
    input_file = '/Users/kabyabasu/Desktop/learning/selenium_task/output.json'
    output_file = '/Users/kabyabasu/Desktop/learning/selenium_task/output_new30.json'

    # Read the JSON file
    data = read_json(input_file)

    # Edit the JSON data
    data = edit_json(data)

    # Write the modified data back to the JSON file
    write_json(output_file, data)

if __name__ == '__main__':
    main()
