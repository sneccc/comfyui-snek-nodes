import json
import os
import random
import re
# Add imports for the web server and response
from server import PromptServer
from aiohttp import web

# Define the directory where prompt JSON files are stored
# Expected location: comfyui-snek-nodes/nodes/random_prompt/
PROMPT_JSON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "random_prompt"))

# --- Cache for JSON data ---
# Structure: { "filename.json": {"modes": ["mode1", "mode2", "all"], "categories": {...}}, ... }
# We store categories too, maybe useful later, but primarily modes for the dynamic dropdown.
JSON_DATA_CACHE = {}
AVAILABLE_JSON_FILES = [] # Keep track of files successfully loaded

def load_and_cache_json_data(directory):
    """Loads modes and categories from all valid JSON files into a cache."""
    global JSON_DATA_CACHE, AVAILABLE_JSON_FILES
    JSON_DATA_CACHE = {} # Clear cache on reload
    AVAILABLE_JSON_FILES = []

    if not os.path.isdir(directory):
        print(f"Warning: JSON directory not found: {directory}. Creating it.")
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            print(f"Error creating directory {directory}: {e}")
            return # Return empty if directory can't be created
        return

    print(f"🐍 Snek Nodes: Scanning for JSON prompts in: {directory}")
    try:
        filenames = sorted([f for f in os.listdir(directory) if f.endswith(".json") and os.path.isfile(os.path.join(directory, f))])
    except Exception as e:
        print(f"Error scanning directory {directory} for JSON files: {e}")
        return

    if not filenames:
         print(f"Warning: No JSON files found in {directory}")
         return

    loaded_count = 0
    for filename in filenames:
        file_path = os.path.join(directory, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # --- Basic Validation ---
            if "categories" not in data or not isinstance(data["categories"], dict) or not data["categories"]:
                 print(f"Warning: Skipping '{filename}'. Missing non-empty 'categories' object.")
                 continue

            file_modes = ["all"] # Always offer "all"
            has_valid_templates = False

            # Check for new "modes" structure
            if "modes" in data and isinstance(data["modes"], dict) and data["modes"]:
                valid_mode_found = False
                for mode_name, templates in data["modes"].items():
                    if isinstance(templates, list) and templates:
                        if mode_name not in file_modes:
                            file_modes.append(mode_name)
                        has_valid_templates = True # Found at least one valid template list
                        valid_mode_found = True
                    else:
                         print(f"Warning: Mode '{mode_name}' in '{filename}' is not a non-empty list. Ignoring this mode entry.")
                # If modes dict exists but no valid modes were found, still allow 'all' if legacy exists
                if not valid_mode_found and not ("templates" in data and isinstance(data["templates"], list) and data["templates"]):
                     print(f"Warning: Skipping '{filename}'. 'modes' object exists but contains no valid template lists, and no legacy 'templates' found.")
                     continue # Skip file if modes is invalid and no legacy fallback

            # Check for legacy "templates" structure (only if no valid modes structure was used)
            elif "templates" in data and isinstance(data["templates"], list) and data["templates"]:
                has_valid_templates = True # Legacy templates exist
                # 'all' is already included
            else:
                # Neither structure found or both empty/invalid
                print(f"Warning: Skipping '{filename}'. No valid 'modes' object or legacy 'templates' list found.")
                continue

            # Only add if there are templates to actually use
            if has_valid_templates:
                JSON_DATA_CACHE[filename] = {
                    "modes": sorted(list(set(file_modes)), key=lambda x: (x != 'all', x)), # Keep 'all' first
                    "categories": data.get("categories", {}), # Store categories
                    # Store templates/modes for runtime use, avoids re-reading file
                    "modes_dict": data.get("modes"),
                    "legacy_templates": data.get("templates")
                }
                AVAILABLE_JSON_FILES.append(filename) # Add to list of usable files
                loaded_count += 1
            else:
                 print(f"Warning: Skipping '{filename}'. No usable templates found despite structure presence.")

        except json.JSONDecodeError as e:
            print(f"Warning: Skipping '{filename}'. Invalid JSON: {e}")
        except FileNotFoundError:
            print(f"Warning: Skipping '{filename}'. File not found unexpectedly.")
        except Exception as e:
            print(f"Warning: Skipping '{filename}'. Error reading/processing: {e}")

    if loaded_count > 0:
        print(f"🐍 Snek Nodes: Successfully loaded {loaded_count} JSON prompt files.")
    else:
        print(f"Error: No valid JSON prompt files were loaded from {directory}. Node may not function.")


# --- Load data at startup ---
load_and_cache_json_data(PROMPT_JSON_DIR)


# --- API Endpoint to get modes for a file ---
@PromptServer.instance.routes.get('/snek/get_modes/{filename}')
async def get_modes_for_file(request):
    filename = request.match_info.get('filename', None)
    if filename and filename in JSON_DATA_CACHE:
        modes = JSON_DATA_CACHE[filename].get("modes", ["all"])
        return web.json_response(modes)
    else:
        # Return only "all" or an empty list if file not found in cache or invalid
        print(f"Debug: API request for modes of unknown file: {filename}")
        return web.json_response(["all"])


class RandomPromptFromJson:
    # Keep track of the available files (now populated by the cache loader)
    json_files = AVAILABLE_JSON_FILES

    # No longer need available_modes class var here

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        # Check if the directory was found and files are available
        if not cls.json_files:
             print("\nERROR: No JSON prompt files found or loaded in expected directory:")
             print(f"{PROMPT_JSON_DIR}")
             print("Please create a 'random_prompt' sub-directory inside 'nodes' with valid .json files.")
             return {
                 "required": {
                     "error": ("STRING", {"default": "No valid JSON files found. Check console.", "multiline": True}),
                     "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                 }
             }

        # Get initial modes for the *first* file to populate dropdown initially
        # JavaScript will update this list dynamically based on json_file selection
        initial_modes = ["all"]
        if cls.json_files and cls.json_files[0] in JSON_DATA_CACHE:
             initial_modes = JSON_DATA_CACHE[cls.json_files[0]].get("modes", ["all"])
        # Ensure "all" is always an option, even if file has no modes somehow
        if "all" not in initial_modes:
            initial_modes.insert(0, "all")

        # --- Build a union list of all modes across every JSON file ---
        #  This ensures the backend validation accepts any mode that exists in any file,
        #  avoiding "Value not in list" errors when a user switches the selected JSON file.
        all_modes_set = set(["all"])
        for cached in JSON_DATA_CACHE.values():
            all_modes_set.update(cached.get("modes", []))

        # Keep "all" first, then alphabetically sort the remaining modes for readability
        all_modes = ["all"] + sorted([m for m in all_modes_set if m != "all"])

        return {
            "required": {
                "json_file": (cls.json_files, ), # Dropdown list
                # Use the comprehensive mode list so any valid mode passes backend validation
                "mode": (all_modes, {"default": "all"}),
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

    # randomize_prompt method can stay mostly the same,
    # it calls _process_prompt which now uses the cache

    def randomize_prompt(self, json_file, mode, seed):
         # Use the existing _process_prompt, but ensure it uses cached data
         return self._process_prompt(json_file, mode, seed)


    def _process_prompt(self, json_file, mode, seed):
        """
        Uses cached data for the selected JSON file to generate a prompt.
        Selects templates based on the chosen mode ('all' or specific).
        Handles fallback to 'all' if the selected mode isn't valid for the file.
        """
        # Check if the selected file is in our cache
        if json_file not in JSON_DATA_CACHE:
             # This might happen if files changed since startup without restart
             print(f"Error: Selected file '{json_file}' not found in cache. Attempting reload.")
             load_and_cache_json_data(PROMPT_JSON_DIR) # Try reloading
             if json_file not in JSON_DATA_CACHE:
                  return (f"ERROR: Selected file '{json_file}' is not loaded or invalid. Check console.",)

        random.seed(seed) # Set seed for reproducibility

        file_data = JSON_DATA_CACHE[json_file]
        cached_modes_dict = file_data.get("modes_dict")
        cached_legacy_templates = file_data.get("legacy_templates")
        available_modes_in_file = file_data.get("modes", ["all"]) # Get modes from cache

        templates_to_use = []
        effective_mode = "none"

        collect_all = False
        use_legacy = False

        # Decide which templates to use based on mode
        if cached_modes_dict: # Prefer new 'modes' structure if available
            if mode == "all":
                collect_all = True
                effective_mode = "all"
            elif mode in cached_modes_dict and isinstance(cached_modes_dict[mode], list) and cached_modes_dict[mode]:
                 # Selected mode exists and is valid in the file's cached modes
                 templates_to_use = cached_modes_dict[mode]
                 effective_mode = mode
            else:
                # Selected mode not found or invalid in file's cache, fallback to 'all'
                if mode != "all": # Avoid redundant warning if user selected "all" anyway
                    print(f"Warning: Mode '{mode}' not valid for '{json_file}'. Available: {available_modes_in_file}. Falling back to using 'all' templates from this file.")
                collect_all = True
                effective_mode = "all (fallback)"

            if collect_all:
                # Collect all templates from all valid modes in the cache
                for mode_name, template_list in cached_modes_dict.items():
                    if isinstance(template_list, list) and template_list:
                        templates_to_use.extend(template_list)
                    # else: warning already printed during caching

        elif cached_legacy_templates: # Fallback to legacy if 'modes' wasn't present/used
            print(f"Info: Using legacy 'templates' structure from cache for '{json_file}'. Mode selection '{mode}' ignored.")
            templates_to_use = cached_legacy_templates
            effective_mode = "legacy"
            use_legacy = True

        # This check should ideally not be needed due to caching logic, but good failsafe
        if not templates_to_use:
             if use_legacy:
                 return (f"ERROR: Legacy 'templates' list cached for '{json_file}' is empty.",)
             elif collect_all:
                  # If collect_all was true but list is empty, it means no valid modes had templates
                  return (f"ERROR: No valid templates found in cache for '{json_file}' under any mode.",)
             else:
                 # This case implies mode was specific but pointed to an empty list (should have been caught earlier)
                 return (f"ERROR: Mode '{mode}' in cache for '{json_file}' has no templates. Effective mode: '{effective_mode}'.",)


        # --- Template selection and placeholder replacement --- 

        # Select a random template from the collected list
        template = random.choice(templates_to_use)

        # Find placeholders in the template
        placeholders = self.find_placeholders(template)

        # Replace placeholders with random choices from categories (using cached categories)
        final_prompt = template
        cached_categories = file_data.get("categories", {})
        unique_placeholders = set(placeholders)
        
        for placeholder in unique_placeholders:
            if placeholder in cached_categories and cached_categories[placeholder]:
                replacement = random.choice(cached_categories[placeholder])
                # Replace all occurrences of this placeholder
                final_prompt = final_prompt.replace("{" + placeholder + "}", replacement)
            else:
                # Add effective mode info to warning
                print(f"Warning: Placeholder '{{{placeholder}}}' found in template from '{json_file}' (effective mode: '{effective_mode}'), but no corresponding category or category is empty in cache. Leaving it unchanged.")

        return (final_prompt,)

# Map the node class for ComfyUI
NODE_CLASS_MAPPINGS = {
    "🐍 Random Prompt From JSON": RandomPromptFromJson
}

# Optional: Map a display name for the node
NODE_DISPLAY_NAME_MAPPINGS = {
    "🐍 Random Prompt From JSON": "Random Prompt From JSON (Snek)"
}

# Comment below is obsolete now
# # Add to NODE_CLASS_MAPPINGS in __init__.py manually or via script
# # NODE_CLASS_MAPPINGS = {
# #     "RandomPromptFromJson": RandomPromptFromJson,
# #     # ... other nodes
# # } 