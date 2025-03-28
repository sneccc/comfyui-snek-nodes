import json
import os
import random
import re

# Define the directory where prompt JSON files are stored
# Expected location: comfyui-snek-nodes/nodes/random_prompt/
PROMPT_JSON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "random_prompt"))

def find_json_files(directory):
    """Find all .json files in the specified directory."""
    if not os.path.isdir(directory):
        print(f"Warning: JSON directory not found: {directory}. Creating it.")
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            print(f"Error creating directory {directory}: {e}")
            return [] # Return empty list if directory can't be created
        return []
    try:
        files = [f for f in os.listdir(directory) if f.endswith(".json") and os.path.isfile(os.path.join(directory, f))]
        return sorted(files)
    except Exception as e:
        print(f"Error scanning directory {directory} for JSON files: {e}")
        return []

# Scan for available JSON files at startup
AVAILABLE_JSON_FILES = find_json_files(PROMPT_JSON_DIR)

class RandomPromptFromJson:
    # Keep track of the available files list
    json_files = AVAILABLE_JSON_FILES

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        # Check if the directory was found and files are available
        if not cls.json_files:
             print("\nERROR: No JSON prompt files found in expected directory:")
             print(f"{PROMPT_JSON_DIR}")
             print("Please create a 'random_prompt' sub-directory inside 'nodes' and place your .json files there.")
             # Provide a dummy input to prevent ComfyUI from crashing
             return {
                 "required": {
                     "error": ("STRING", {"default": "No JSON files found. Check console.", "multiline": True}),
                     "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                 }
             }

        return {
            "required": {
                "json_file": (cls.json_files, ), # Dropdown list
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("randomized_prompt",)
    FUNCTION = "randomize_prompt"
    CATEGORY = "🐍 Snek Nodes"

    def find_placeholders(self, text):
        """Find all placeholders like {placeholder} in the text."""
        return re.findall(r"\{([^}]+)\}", text)

    # Added json_file parameter from the dropdown
    def randomize_prompt(self, json_file, seed):
        """
        Loads data from the selected JSON file, selects a random template,
        and fills placeholders with random items from categories.
        JSON files should be placed in the 'nodes/random_prompt/' directory.
        Structure: {"templates": ["... {category} ..."], "categories": {"category": ["item1", "item2"]}}
        Inspired by Noodle Soup Prompts pantry format: https://raw.githubusercontent.com/WASasquatch/noodle-soup-prompts/main/nsp_pantry.json
        """
        # Handle the error case where no files were found
        if not self.json_files:
            return ("ERROR: No JSON files found. See console.",)

        random.seed(seed) # Set seed for reproducibility

        # Construct the full path to the selected JSON file
        try:
            actual_path = os.path.abspath(os.path.join(PROMPT_JSON_DIR, json_file))
            if not os.path.exists(actual_path):
                 # This shouldn't happen if the dropdown is populated correctly, but check anyway
                 raise FileNotFoundError(f"Selected JSON file '{json_file}' not found in '{PROMPT_JSON_DIR}'")
        except Exception as e:
            raise RuntimeError(f"Error constructing path for selected JSON file: {e}")

        # --- Loading and processing logic remains largely the same ---
        try:
            with open(actual_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {actual_path}. Error: {e}")
        except FileNotFoundError:
             # Should be caught by earlier check, but handle defensively
             raise FileNotFoundError(f"JSON file not found at expected location: {actual_path}")
        except Exception as e:
            raise RuntimeError(f"Error reading JSON file: {actual_path}. Error: {e}")

        if "templates" not in data or not data["templates"]:
            raise ValueError(f"JSON file '{actual_path}' must contain a non-empty 'templates' list.")
        if "categories" not in data or not data["categories"]:
             raise ValueError(f"JSON file '{actual_path}' must contain a non-empty 'categories' object.")

        # Select a random template
        template = random.choice(data["templates"])

        # Find placeholders in the template
        placeholders = self.find_placeholders(template)

        # Replace placeholders with random choices from categories
        final_prompt = template
        unique_placeholders = set(placeholders) # Process each type of placeholder only once
        
        for placeholder in unique_placeholders:
            if placeholder in data["categories"] and data["categories"][placeholder]:
                replacement = random.choice(data["categories"][placeholder])
                # Replace all occurrences of this placeholder
                final_prompt = final_prompt.replace("{" + placeholder + "}", replacement)
            else:
                # Provide more context in the warning
                print(f"Warning: Placeholder '{{{placeholder}}}' found in template '{template}' from file '{json_file}', but no corresponding category or category is empty in JSON. Leaving it unchanged.")

        return (final_prompt,)

# Map the node class for ComfyUI
NODE_CLASS_MAPPINGS = {
    "🐍 Random Prompt From JSON": RandomPromptFromJson
}

# Comment below is obsolete now
# # Add to NODE_CLASS_MAPPINGS in __init__.py manually or via script
# # NODE_CLASS_MAPPINGS = {
# #     "RandomPromptFromJson": RandomPromptFromJson,
# #     # ... other nodes
# # } 