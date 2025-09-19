import os

# Import nodes and their mappings
from .nodes.aesthetic import NODE_CLASS_MAPPINGS as Aesthetic_MAPPING
from .nodes.send_to_Eagle import NODE_CLASS_MAPPINGS as Eagle_MAPPING
from .nodes.experimental import NODE_CLASS_MAPPINGS as Experimental_MAPPING

# --- IMPORTANT: Import node file directly to register API routes ---
# import .nodes.random_prompt_node  <-- REMOVED
# --- Then import its mappings ---
from .nodes.random_prompt_node import NODE_CLASS_MAPPINGS as RandomPrompt_MAPPING
from .nodes.sqlite import NODE_CLASS_MAPPINGS as SQLite_MAPPING

# --- IMPORTANT: Define the directory for JS files ---
# This tells ComfyUI where to find your JavaScript file(s)
WEB_DIRECTORY = "js"

# Combine all node mappings
NODE_CLASS_MAPPINGS = {
    **Aesthetic_MAPPING,
    **Eagle_MAPPING,
    **Experimental_MAPPING,
    **RandomPrompt_MAPPING,
    **SQLite_MAPPING,
}

# Export mappings and the web directory name
__all__ = ["NODE_CLASS_MAPPINGS", "WEB_DIRECTORY"]
