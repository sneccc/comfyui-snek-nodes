from .nodes.aesthetic import NODE_CLASS_MAPPINGS as Aesthetic_MAPPING
from .nodes.send_to_Eagle import NODE_CLASS_MAPPINGS as Eagle_MAPPING
from .nodes.experimental import NODE_CLASS_MAPPINGS as Experimental_MAPPING
from .nodes.random_prompt_node import NODE_CLASS_MAPPINGS as RandomPrompt_MAPPING

NODE_CLASS_MAPPINGS = {
    **Aesthetic_MAPPING,
    **Eagle_MAPPING,
    **Experimental_MAPPING,
    **RandomPrompt_MAPPING
}
__all__ = ["NODE_CLASS_MAPPINGS"]
